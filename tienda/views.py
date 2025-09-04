import os
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect

from django.conf import settings
from .forms import LoginForm, RegistroUsuarioForm, ArticuloForm, ProveedorForm, ClienteForm, EditarUsuarioForm
from .models import TblUsuario, TblProducto, TblProveedor, TblCliente, TblVenta, TblDetVenta, TblEntrada,TblTipoDocAlmacen, TblDetEntrada, TblMetodoPago, TblSalida, TblDetSalida, TblFinanciamiento, TblDetFinanciamiento, TblTipoUsuario, TblCargo, TblKardex, TblProductoSerie
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.db.models import Max, Sum, Q, F, Value, Count, Case, When, IntegerField
from django.db.models.functions import Concat
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import transaction, connection, InternalError
from decimal import Decimal
from django.template.loader import render_to_string
from django.template.loader import get_template
from django.urls import reverse
from django.utils.http import urlencode
from xhtml2pdf import pisa
from num2words import num2words
from django.contrib.auth.hashers import make_password
from utils.email import send_mail_api
import random
import string
import json
import traceback

import requests
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_GET, require_POST

from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime, parse_date

from calendar import monthrange
from collections import defaultdict, OrderedDict


User = get_user_model()

# Create your views here.
def solo_personal(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.tipo_usuario.tipo_usuario_descrip.lower() != 'cliente':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Acceso no autorizado.")
    return _wrapped_view


# ---------- Helpers ----------
def month_key(dt):
    return dt.strftime("%Y-%m")

def month_label(dt):
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return f"{meses[dt.month-1]} {dt.year}"

def first_day(dt):
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def last_day(dt):
    last = monthrange(dt.year, dt.month)[1]
    return dt.replace(day=last, hour=23, minute=59, second=59, microsecond=999999)

def last_n_months(n=6, tz=None):
    now = timezone.localtime(timezone.now(), tz) if tz else timezone.localtime()
    months = []
    cur = now.replace(day=1)
    for i in range(n-1, -1, -1):
        m = (cur - timedelta(days=1)).replace(day=1) if i != 0 else cur
        # recalcular correcto: mover hacia atrás i meses
    months = []
    base = now.replace(day=15)  # para evitar bordes
    for i in range(n-1, -1, -1):
        m = (base - timedelta(days=30*i))
        m = m.replace(day=1)
        months.append(m)
    # normalizar por año/mes únicos ordenados
    ordered = OrderedDict()
    for m in sorted(months, key=lambda d:(d.year, d.month)):
        key = (m.year, m.month)
        if key not in ordered:
            ordered[key] = m
    return list(ordered.values())[-n:]

def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d")


@solo_personal
def home(request):
    # KPI circulares (cuenta inicial para la primera sección)
    clientes = TblCliente.objects.count()
    proveedores = TblProveedor.objects.count()
    motos = TblProducto.objects.filter(prod_tipo__iexact="MOTO").count()
    accesorios = TblProducto.objects.filter(prod_tipo__iexact="ACCESORIO").count()

    # Fechas por defecto de la 3ra sección
    tz = timezone.get_current_timezone()
    hoy = timezone.localtime(timezone.now(), tz).date()
    inicio_mes = hoy.replace(day=1)

    context = {
        "kpi_clientes": clientes,
        "kpi_proveedores": proveedores,
        "kpi_motos": motos,
        "kpi_accesorios": accesorios,
        "default_start": inicio_mes.strftime("%Y-%m-%d"),
        "default_end": hoy.strftime("%Y-%m-%d"),
    }
    return render(request, 'tienda/home.html', context)


# ---------- API: Overview (secciones 1 y 2) ----------
def api_dashboard_overview(request):
    tz = timezone.get_current_timezone()
    months = last_n_months(6, tz)
    labels = [month_label(m) for m in months]
    month_ranges = [(first_day(m), last_day(m)) for m in months]

    # Map de métodos de pago
    mp_map = dict(TblMetodoPago.objects.values_list("metodo_pago_id", "metodo_pago_descrip"))
    tipos_pago = ["EFECTIVO", "CREDITO", "MIXTO"]

    # Resumen ventas últimos 6 meses por tipo y totales
    resumen_grid = []
    barras_totales = []
    stacked_totales_por_tipo = {t: [] for t in tipos_pago}


    for (start, end), lab in zip(month_ranges, labels):
        ventas_qs = TblVenta.objects.filter(
            venta_fecha_venta__range=(start, end),
            venta_eliminado=False
        )

        # Totales por tipo de pago
        fila = {"mes": lab}
        total_mes = ventas_qs.aggregate(total=Sum("venta_total"))["total"] or 0

        # Conteos y sumas por tipo
        pagos = defaultdict(lambda: {"n": 0, "total": 0})
        for v in ventas_qs.select_related("metodo_pago"):
            tipo = (v.metodo_pago.metodo_pago_descrip or "").strip().upper()
            if tipo not in tipos_pago:
                # normaliza nombres variantes
                if "EFEC" in tipo: tipo = "EFECTIVO"
                elif "CRED" in tipo: tipo = "CREDITO"
                elif "MIX" in tipo: tipo = "MIXTO"
                else: tipo = "EFECTIVO"
            pagos[tipo]["n"] += 1
            pagos[tipo]["total"] += float(v.venta_total)

        for t in tipos_pago:
            fila[f"{t.lower()}_n"] = pagos[t]["n"]
            fila[f"{t.lower()}_total"] = round(pagos[t]["total"], 2)
            stacked_totales_por_tipo[t].append(round(pagos[t]["total"], 2))

        fila["total_mes"] = round(float(total_mes), 2)
        resumen_grid.append(fila)
        barras_totales.append(round(float(total_mes), 2))

    # Utilidad por mes (formula por venta y se suma)
    utilidades = []
    ventas_canal_tienda = []
    ventas_canal_online = []
    for (start, end) in month_ranges:
        ventas_mes = TblVenta.objects.filter(
            venta_fecha_venta__range=(start, end),
            venta_eliminado=False
        )
        util = 0.0
        tienda_n = 0
        online_n = 0
        for v in ventas_mes:
            vt = float(v.venta_total)
            u = (vt - (vt / 1.2)) / 1.8
            util += u
            if v.venta_online:
                online_n += 1
            else:
                tienda_n += 1
        utilidades.append(round(util, 2))
        ventas_canal_tienda.append(tienda_n)
        ventas_canal_online.append(online_n)

    # Más vendido por tipo (por mes)
    top_cant_moto = []
    top_cant_accesorio = []
    top_nombre_moto = []
    top_nombre_accesorio = []

    for (start, end) in month_ranges:
        # Detalle de venta en rango
        det = TblDetVenta.objects.filter(
            venta__venta_fecha_venta__range=(start, end),
            venta__venta_eliminado=False
        ).select_related("prod", "venta")

        # Agrupar por producto
        sum_por_prod = defaultdict(int)
        tipo_por_prod = {}
        nombre_por_prod = {}
        for d in det:
            if not d.prod_id:
                continue
            sum_por_prod[d.prod_id] += int(d.det_venta_cantidad)
            tipo_por_prod[d.prod_id] = (d.prod.prod_tipo or "").upper()
            nombre_por_prod[d.prod_id] = d.prod.prod_nombre

        # Encontrar max por tipo
        max_moto, nombre_moto = 0, ""
        max_acc, nombre_acc = 0, ""
        for pid, cant in sum_por_prod.items():
            tipo = tipo_por_prod.get(pid, "")
            if tipo == "MOTO":
                if cant > max_moto:
                    max_moto = cant
                    nombre_moto = nombre_por_prod.get(pid, "")
            elif tipo == "ACCESORIO":
                if cant > max_acc:
                    max_acc = cant
                    nombre_acc = nombre_por_prod.get(pid, "")

        top_cant_moto.append(max_moto)
        top_cant_accesorio.append(max_acc)
        top_nombre_moto.append(nombre_moto)
        top_nombre_accesorio.append(nombre_acc)

    data = {
        "labels_6m": labels,
        "resumen": resumen_grid,
        "barras_totales": barras_totales,
        "stacked_por_tipo": {k: v for k, v in stacked_totales_por_tipo.items()},
        "utilidades": utilidades,
        "ventas_canal_tienda": ventas_canal_tienda,
        "ventas_canal_online": ventas_canal_online,
        "top_mes_moto": top_cant_moto,
        "top_mes_accesorio": top_cant_accesorio,
        "nombre_mes_moto": top_nombre_moto,
        "nombre_mes_accesorio": top_nombre_accesorio,
    }
    return JsonResponse(data)

# ---------- API: Estado de artículos (2.3) ----------
def api_dashboard_state(request):
    # Solo productos con Kardex
    kardex = TblKardex.objects.select_related("prod").all()

    estado_counts = {"agotado": 0, "por_agotar": 0, "ok": 0}
    total_items = 0
    detalle = []

    for k in kardex:
        total_items += 1
        if k.kardex_stock_actual == 0:
            estado = "agotado"
        elif k.kardex_stock_actual <= k.kardex_stock_minimo:
            estado = "por_agotar"
        else:
            estado = "ok"
        estado_counts[estado] += 1
        detalle.append({
            "prod_id": k.prod_id,
            "nombre": k.prod.prod_nombre,
            "stock": k.kardex_stock_actual,
            "minimo": k.kardex_stock_minimo,
            "estado": estado,
        })

    percentages = {k: (round((v * 100.0 / total_items), 2) if total_items else 0) for k, v in estado_counts.items()}
    data = {
        "total": total_items,
        "counts": estado_counts,
        "percentages": percentages,
        "detalle": detalle[:200],  # por si hay muchos; puedes paginar si deseas
    }
    return JsonResponse(data)

# ---------- API: Filtro por rango (Sección 3) ----------
def api_dashboard_filter(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    if not start or not end:
        return HttpResponseBadRequest("Parámetros 'start' y 'end' son requeridos (YYYY-MM-DD).")
    try:
        start_dt = timezone.make_aware(datetime.combine(parse_date(start).date(), datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(parse_date(end).date(), datetime.max.time()))
    except Exception:
        return HttpResponseBadRequest("Formato de fecha inválido. Use YYYY-MM-DD.")

    if end_dt < start_dt:
        return HttpResponseBadRequest("La fecha fin no puede ser menor que la fecha inicio.")

    # KPIs
    total_compras = TblEntrada.objects.filter(entrada_fecha__range=(start_dt, end_dt)) \
        .aggregate(s=Sum("entrada_costo_total"))["s"] or 0
    total_ventas = TblSalida.objects.filter(salida_fecha__range=(start_dt, end_dt), salida_eliminado=False) \
        .aggregate(s=Sum("salida_costo_total"))["s"] or 0

    util = 0.0
    for s in TblSalida.objects.filter(salida_fecha__range=(start_dt, end_dt), salida_eliminado=False):
        if s.salida_costo_total is None: continue
        vt = float(s.salida_costo_total)
        util += (vt - (vt / 1.2)) / 1.8

    # Top 8 artículos más vendidos (por det_salida_cantidad)
    det = TblDetSalida.objects.filter(
        salida__salida_fecha__range=(start_dt, end_dt),
        salida__salida_eliminado=False
    ).select_related("prod", "salida")

    cant_por_art = defaultdict(int)
    for d in det:
        if d.det_salida_cantidad:
            cant_por_art[d.prod_id] += int(d.det_salida_cantidad)

    top8 = sorted(cant_por_art.items(), key=lambda x: x[1], reverse=True)[:8]
    # mapear nombres
    nombres_map = dict(TblProducto.objects.filter(prod_id__in=[pid for pid, _ in top8]).values_list("prod_id", "prod_nombre"))
    top8_labels = [nombres_map.get(pid, f"Prod {pid}") for pid, _ in top8]
    top8_values = [qty for _, qty in top8]

    # Ventas diarias (áreas apiladas: usaremos 1 serie con total; si quieres apilar por canal, se puede extender)
    diarios_map = defaultdict(float)
    salidas = TblSalida.objects.filter(salida_fecha__range=(start_dt, end_dt), salida_eliminado=False)
    for s in salidas:
        if s.salida_costo_total is None: continue
        d = timezone.localtime(s.salida_fecha).date().isoformat()
        diarios_map[d] += float(s.salida_costo_total)
    dias = sorted(diarios_map.keys())
    dias_values = [round(diarios_map[d], 2) for d in dias]

    # Top 5 vendedores por número de ventas en rango
    try:
        id_cargo_vendedor = TblCargo.objects.get(cargo_id=F("cargo_id"), cargo_emp_descrip__iexact="Vendedor")
    except:
        id_cargo_vendedor = None
    # Si no encontramos el cargo exacto, filtramos por texto
    vendedores_ids = list(TblUsuario.objects.filter(Q(cargo__cargo_emp_descrip__iexact="Vendedor") | Q(cargo__cargo_emp_descrip__iexact="Administrador")).values_list("id", flat=True))
    if not vendedores_ids:
        vendedores_ids = list(TblUsuario.objects.filter(Q(cargo__cargo_emp_descrip__icontains="Vended") | Q(cargo__cargo_emp_descrip__icontains="Admin")).values_list("id", flat=True))

    ventas_por_vendedor = (TblSalida.objects
        .filter(salida_fecha__range=(start_dt, end_dt), salida_eliminado=False, usuario_id__in=vendedores_ids)
        .values("usuario_id")
        .annotate(n=Count("salida_id"))
        .order_by("-n")[:5])

    nombres_vendedores = dict(TblUsuario.objects.filter(id__in=[v["usuario_id"] for v in ventas_por_vendedor])
                              .values_list("id", "username"))
    top5_v_labels = [nombres_vendedores.get(v["usuario_id"], f"User {v['usuario_id']}") for v in ventas_por_vendedor]
    top5_v_values = [v["n"] for v in ventas_por_vendedor]

    # Pie 3D-like (cantidad artículos por tipo en rango)
    det_sal = TblDetSalida.objects.filter(
        salida__salida_fecha__range=(start_dt, end_dt),
        salida__salida_eliminado=False
    ).select_related("prod")

    qty_tipo = {"MOTO": 0, "ACCESORIO": 0}
    for d in det_sal:
        t = (d.prod.prod_tipo or "").upper()
        if t in qty_tipo:
            qty_tipo[t] += int(d.det_salida_cantidad or 0)

    # Donut: ventas por canal en rango
    canal_tienda = TblSalida.objects.filter(salida_fecha__range=(start_dt, end_dt), salida_eliminado=False, salida_online=False).count()
    canal_online = TblSalida.objects.filter(salida_fecha__range=(start_dt, end_dt), salida_eliminado=False, salida_online=True).count()

    # Half-donut: online vs entregado
    online_total = canal_online
    online_entregado = TblSalida.objects.filter(
        salida_fecha__range=(start_dt, end_dt), salida_eliminado=False, salida_online=True, salida_online_entregado=True
    ).count()
    online_pendiente = max(0, online_total - online_entregado)

    data = {
        "kpis": {
            "compras": round(float(total_compras), 2),
            "ventas": round(float(total_ventas), 2),
            "utilidad": round(float(util), 2),
        },
        "top8": {
            "labels": top8_labels,
            "values": top8_values
        },
        "diarios": {
            "labels": dias,
            "values": dias_values
        },
        "top_vendedores": {
            "labels": top5_v_labels,
            "values": top5_v_values
        },
        "por_tipo": {
            "labels": ["MOTO", "ACCESORIO"],
            "values": [qty_tipo["MOTO"], qty_tipo["ACCESORIO"]]
        },
        "canal": {
            "labels": ["Tienda", "Online"],
            "values": [canal_tienda, canal_online]
        },
        "online_entrega": {
            "labels": ["Entregado", "Pendiente"],
            "values": [online_entregado, online_pendiente],
            "total_online": online_total
        }
    }
    return JsonResponse(data)

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # Obtener los datos del formulario
            usuario = form.cleaned_data['usuario']
            password = form.cleaned_data['password']

            # Buscar el usuario de forma segura
            user_qs = TblUsuario.objects.filter(username=usuario)  #obtiene todos los registros que coinciden con el username
            if user_qs.exists():
                if user_qs.count() > 1:
                    form.add_error('usuario', 'Hay múltiples usuarios con este nombre. Contacta al administrador.')
                else:
                    # Intentamos autenticar (validar contraseña)
                    user = authenticate(request, username=usuario, password=password)
                    if user is not None:
                        login(request, user)
                        request.session['id'] = user.id     # Se puede usar user.usuario_id si se prefiere
                        
                        try:
                            cliente = TblCliente.objects.get(usuario=user)
                            request.session['cliente_id'] = cliente.id
                        except TblCliente.DoesNotExist:
                            request.session['cliente_id'] = None

                        if user.usuario_cambiopwd:
                            return redirect('cambiar_contrasena')  # Vista temporal para cambio de contraseña

                        tipo_usuario = user.tipo_usuario.tipo_usuario_descrip.lower()
                        if tipo_usuario == 'cliente':
                            return redirect('inicio')  # URL que corresponde a la tienda online
                        else:
                            return redirect('home')  # página interna para empleados/admin (personal autorizado)
                        
                    else:
                        form.add_error('password', 'Contraseña incorrecta') # Añadir error para la contraseña incorrecta
                        #form.add_error(None, 'Contraseña incorrecta')
            else:
                form.add_error('usuario', 'El nombre de usuario no existe')
    else:
        form = LoginForm()

    return render(request, 'tienda/login.html', {'form': form})

def recuperar_cuenta(request):
    # Generar contraseña aleatoria
    def generar_contrasena():
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip()

        usuarios = TblUsuario.objects.filter(usuario_email=correo)

        if not usuarios.exists():
            return JsonResponse({'error': 'No existe ningún usuario con ese correo.'})

        if usuarios.count() > 1:
            return JsonResponse({'error': 'Hay múltiples usuarios con ese correo. Contacta al administrador.'})

        user = usuarios.first()
        
        # Generar nueva contraseña aleatoria
        nueva_pwd = generar_contrasena()
        
        user.password = make_password(nueva_pwd)
        user.usuario_cambiopwd = True
        user.save()

        # Enviar correo
        try:
            send_mail_api(
                subject='Recuperación de cuenta - Nexus Motos',
                message=f'Su usuario es: {user.username}\nNueva contraseña: {nueva_pwd}',
                recipient_list=[correo],
            )
            return JsonResponse({'ok': True, 'mensaje': f'Se envió un correo a {correo} con sus credenciales.'})
        except Exception as e:
            return JsonResponse({'error': 'Error al enviar el correo. Intente más tarde.'})

    # 👇 Si es GET, mostrar el formulario HTML
    return render(request, 'tienda/recuperar_cuenta.html')

def signoup (request):
    logout(request) 
    return redirect('home')

@require_GET
@solo_personal
def consultar_dni(request):
    dni = request.GET.get('dni')
    if not dni:
        return JsonResponse({'success': False, 'error': 'DNI no proporcionado.'})
    
    try:
        token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzODgxMyIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6ImNvbnN1bHRvciJ9.t2fH0zWmEWyR1_hfVRGS_fGJvAdobiIC41_I9dBQ7ZM'
        url = f"https://api.factiliza.com/v1/dni/info/{dni}"
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, headers=headers)
        #print(response.text)
        if response.status_code == 200:
            data = response.json()
            return JsonResponse({
                'success': True,
                'nombres': data.get('data', {}).get('nombres'), #data['data']['nombres']
                'apellido_paterno': data.get('data', {}).get('apellido_paterno'),
                'apellido_materno': data.get('data', {}).get('apellido_materno'),
                'direccion': data.get('data', {}).get('direccion'),
            })
        else:
            return JsonResponse({'success': False, 'error': 'DNI no encontrado.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

#### USUARIOS ####
@solo_personal
def lista_usuarios(request):
    usuarios  = TblUsuario.objects.all()

    context = {
        'breadcrumbs': [['Usuarios', '']],
        'menu_padre': 'accesos',
        'menu_hijo': 'usuarios',
        'usuarios': usuarios,
    }

    return render(request, 'tienda/lista_usuarios.html', context)

@require_GET
@solo_personal
def verificar_username(request):
    username = request.GET.get('username', '')
    existe = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'existe': existe})

@solo_personal
def verificar_datos(request):
    numDoc = request.GET.get('numDoc')
    email = request.GET.get('email')
    existeDoc = TblUsuario.objects.filter(usuario_nrodocumento=numDoc).exclude(tipo_usuario__tipo_usuario_descrip__iexact="cliente").exists() if numDoc else False
    existeEmail = TblUsuario.objects.filter(usuario_email=email).exclude(tipo_usuario__tipo_usuario_descrip__iexact="cliente").exists() if email else False

    return JsonResponse({'existsDoc': existeDoc, 'existsEmail': existeEmail})

@solo_personal
def agregar_usuario(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                usuario = form.save(commit=False)
                usuario.save()
                return redirect('lista_usuarios')
            except Exception as e:
                print(f'Error al guardar el usuario: {e}')  # Esto mostrará el error exacto
        else:
            print('Formulario inválido:', form.errors)
    else:
        form = RegistroUsuarioForm()

    context = {
        'breadcrumbs': [['Usuarios','/lista_usuarios/'],['Registro de nuevo usuario','']],
        'menu_padre': 'accesos',
        'menu_hijo': 'usuarios',
        'form': form,
    }
    return render(request, 'tienda/agregar_usuario.html', context)

@solo_personal
def editar_usuario(request, id):
    usuario = get_object_or_404(TblUsuario, id=id)

    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect('lista_usuarios')
        else:
            print(form.errors)
    else:
        form = EditarUsuarioForm(instance=usuario)

    context = {
        'breadcrumbs': [['Usuarios','/lista_usuarios/'],['Edición de usuario','']],
        'menu_padre': 'accesos',
        'menu_hijo': 'usuarios',
        'form': form,
        'usuario': usuario,
    }
    return render(request, 'tienda/editar_usuario.html', context)

@solo_personal
def detalle_usuario(request, id):
    usuario = get_object_or_404(TblUsuario, pk=id)
    
    context = {
        'breadcrumbs': [['Usuarios','/lista_usuarios/'],['Detalle de usuario','']],
        'menu_padre': 'accesos',
        'menu_hijo': 'usuarios',
        'usuario': usuario,
    }

    return render(request, 'tienda/detalle_usuario.html', context)

#### ARTICULOS ####
@solo_personal
def lista_articulos(request):
    productos = TblProducto.objects.all().select_related('tblkardex')
    
    for producto in productos:
        producto.descuento_porcentaje = int(producto.prod_porcenta_dcto or 0)
        if hasattr(producto, 'tblkardex'):
            producto.stock_actual = producto.tblkardex.kardex_stock_actual
        else:
            producto.stock_actual = 0

    context = {
        'breadcrumbs': [['Artículos', '']],
        'menu_padre': 'almacen',
        'menu_hijo': 'articulos',
        'productos': productos,
    }

    return render(request, 'tienda/lista_articulos.html', context)

@solo_personal
def verificar_articulo_existe(request):
    marca = request.GET.get('marca')
    modelo = request.GET.get('modelo')

    existe = TblProducto.objects.filter(prod_marca=marca, prod_modelo=modelo).exists()
    return JsonResponse({'existe': existe})

@solo_personal
def agregar_articulos(request):
    if request.method == 'POST':
        form = ArticuloForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                producto = form.save(commit=False)
                imagen = request.FILES.get('imagen_archivo')

                if imagen:
                    ruta_destino = os.path.join(settings.BASE_DIR, 'staticfiles', 'tienda', 'img')
                    os.makedirs(ruta_destino, exist_ok=True)
                    path_final = os.path.join(ruta_destino, imagen.name)

                    with open(path_final, 'wb+') as destino:
                        for chunk in imagen.chunks():
                            destino.write(chunk)

                    producto.prod_imagen = imagen.name  # solo el nombre del archivo

                producto.prod_fecha_registro = datetime.now()
                producto.save()
                return redirect('lista_articulos')
            except Exception as e:
                print(f'Error al guardar el producto: {e}')  # Esto mostrará el error exacto
        else:
            print('Formulario inválido:', form.errors)
    else:
        form = ArticuloForm()

    context = {
        'breadcrumbs': [['Artículos','/lista_articulos/'],['Registro de nuevo artículo','']],
        'menu_padre': 'almacen',
        'menu_hijo': 'articulos',
        'form': form,
    }

    return render(request, 'tienda/agregar_articulos.html', context)

@solo_personal
def editar_articulo(request, producto_id):
    producto = get_object_or_404(TblProducto, prod_id=producto_id)

    # Verificamos si el producto tiene una imagen
    tiene_imagen = bool(producto.prod_imagen)

    if request.method == 'POST':
        form = ArticuloForm(request.POST, request.FILES, instance=producto, tiene_imagen=tiene_imagen)
        
        if form.is_valid():
            producto = form.save(commit=False)
            imagen = request.FILES.get('imagen_archivo')

            if imagen:
                ruta_destino = os.path.join(os.path.dirname(__file__), '..', 'staticfiles', 'tienda', 'img')
                os.makedirs(ruta_destino, exist_ok=True)
                path_final = os.path.join(ruta_destino, imagen.name)
                with open(path_final, 'wb+') as destino:
                    for chunk in imagen.chunks():
                        destino.write(chunk)
                producto.prod_imagen = imagen.name

            producto.save()
            print("Producto editado exitosamente")
            return redirect('lista_articulos')
        else:
            print("Formulario inválido:")
            print(form.errors)
    else:
        form = ArticuloForm(instance=producto, tiene_imagen=tiene_imagen)

    context = {
        'breadcrumbs': [['Artículos','/lista_articulos/'],['Edición de artículo','']],
        'menu_padre': 'almacen',
        'menu_hijo': 'articulos',
        'form': form,
        'producto': producto,
    }

    return render(request, 'tienda/editar_articulo.html', context)

@solo_personal
def detalle_articulo(request, producto_id):
    producto = get_object_or_404(TblProducto, pk=producto_id)
    descuento_porcentaje = int(producto.prod_porcenta_dcto)

    # Obtener el stock desde el Kardex
    try:
        precio_vigente = float(producto.tblkardex.kardex_precio_vigente)*1.2
    except TblKardex.DoesNotExist:
        precio_vigente = 0

    context = {
        'breadcrumbs': [['Artículos','/lista_articulos/'],['Detalle de artículo','']],
        'menu_padre': 'almacen',
        'menu_hijo': 'articulos',
        'producto': producto,
        'descuento_porcentaje': descuento_porcentaje,
        'precio_vigente': precio_vigente,
    }

    return render(request, 'tienda/detalle_articulo.html', context)

@require_POST
@solo_personal
def cambiar_estado_articulo(request, producto_id):
    producto = get_object_or_404(TblProducto, prod_id=producto_id)
    producto.prod_estado = not producto.prod_estado
    producto.save()

    estado = "activado" if producto.prod_estado else "desactivado"
    return JsonResponse({"message": f'Artículo "{producto.prod_nombre}" ha sido {estado} correctamente.'})

#### PROVEEDORES ####
@solo_personal
def lista_proveedores(request):
    proveedores = TblProveedor.objects.all()

    context = {
        'breadcrumbs': [['Proveedores', '']],
        'menu_padre': 'compras',
        'menu_hijo': 'proveedores',
        'proveedores': proveedores,
    }

    return render(request, 'tienda/lista_proveedores.html', context)

@solo_personal
def verificar_proveedor(request):
    nombre = request.GET.get('nombre')
    ruc = request.GET.get('ruc')
    email = request.GET.get('email')
    telefono = request.GET.get('telefono')

    existeNombre= TblProveedor.objects.filter(proveedor_nombre=nombre).exists() if nombre else False
    existeRuc = TblProveedor.objects.filter(proveedor_ruc=ruc).exists() if ruc else False
    existeEmail = TblProveedor.objects.filter(proveedor_email=email).exists() if email else False
    existeTelefono = TblProveedor.objects.filter(proveedor_telefono=telefono).exists() if telefono else False

    return JsonResponse({'existeEmail': existeEmail, 'existeNombre': existeNombre, 'existeRuc': existeRuc, 'existeTelefono': existeTelefono})

@solo_personal
def agregar_proveedor(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                proveedor = form.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'proveedor': {
                            'id': proveedor.proveedor_id,
                            'nombre': proveedor.proveedor_nombre
                        }
                    })
                else:
                    return redirect('lista_proveedores')
            except Exception as e:
                # Captura cualquier error inesperado al guardar
                print(f'Error al guardar el proveedor: {e}')  # Esto mostrará el error exacto
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'Ocurrió un error al guardar el proveedor: ' + str(e)
                    })
                else:
                    messages.error(request, f"Ocurrió un error al guardar el proveedor: {str(e)}")
                    context = {
                        'breadcrumbs': [['Proveedores','/lista_proveedores/'],['Registro de nuevo proveedor','']],
                        'menu_padre': 'compras',
                        'menu_hijo': 'proveedores',
                        'form': form,
                    }
                    return render(request, 'tienda/agregar_proveedor.html', context)
        else:
            print('Formulario inválido:', form.errors)
            # Si el formulario es inválido
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                html = render_to_string('tienda/agregar_proveedor_form.html', {'form': form}, request=request)
                return JsonResponse({'success': False, 'html': html})
    else:
        form = ProveedorForm()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html = render_to_string('tienda/agregar_proveedor_form.html', {'form': form}, request=request)
            return JsonResponse({'success': False, 'html': html})

    context = {
        'breadcrumbs': [['Proveedores','/lista_proveedores/'],['Registro de nuevo proveedor','']],
        'menu_padre': 'compras',
        'menu_hijo': 'proveedores',
        'form': form,
    }

    return render(request, 'tienda/agregar_proveedor.html', context)

@solo_personal
def editar_proveedor(request, prov_id):
    proveedor = get_object_or_404(TblProveedor, proveedor_id = prov_id)
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)

        if form.is_valid():
            proveedor.save()
            return redirect('lista_proveedores')
            
        else:
            print(form.errors)
    else:
        form = ProveedorForm(instance=proveedor)

    context = {
        'breadcrumbs': [['Proveedores','/lista_proveedores/'],['Edición de proveedor','']],
        'menu_padre': 'compras',
        'menu_hijo': 'proveedores',
        'form': form,
        'proveedor': proveedor,
    }

    return render(request, 'tienda/editar_proveedor.html', context)

@solo_personal
def detalle_proveedor(request, prov_id):
    proveedor = get_object_or_404(TblProveedor, pk=prov_id)
    
    context = {
        'breadcrumbs': [['Proveedores','/lista_proveedores/'],['Detalle de proveedor','']],
        'menu_padre': 'compras',
        'menu_hijo': 'proveedores',
        'proveedor': proveedor,
    }

    return render(request, 'tienda/detalle_proveedor.html', context)

#### INGRESOS ####
@solo_personal
def lista_ingresos(request):
    ingresos = TblEntrada.objects.select_related(
        'proveedor', 'tipo_doc_almacen', 'usuario'
    ).all()

    context = {
        'breadcrumbs': [['Ingresos', '']],
        'menu_padre': 'compras',
        'menu_hijo': 'ingresos',
        'ingresos': ingresos,
    }

    return render(request, 'tienda/lista_ingresos.html', context)

@solo_personal
def validar_serie(request):
    try:
        serie = request.GET.get('serie', '').strip()
        existe = TblProductoSerie.objects.filter(prod_ser_serie=serie).exists()
        return JsonResponse({'existe': existe})
    except Exception as e:
        print(f'Error al consultar serie: {e}')

@transaction.atomic
@solo_personal
def agregar_ingresos(request):
    if request.method == "POST":
        try:
            proveedor_id = request.POST.get("proveedor_id")
            tipo_doc_id = request.POST.get("tipo_doc")
            entrada_num_doc = request.POST.get("entrada_num_doc")
            #entrada_fecha = request.POST.get("entrada_fecha")
            entrada_igv = float(request.POST.get("entrada_igv", 0))
            entrada_subtotal = float(request.POST.get("subtotal_entrada") or 0)
            entrada_monto_igv = float(request.POST.get("montoIgv_entrada") or 0)
            entrada_total = float(request.POST.get("total_entrada") or 0)

            articulos_json = request.POST.get("articulos")  # Este es un JSON con los productos
            articulos = json.loads(articulos_json)

            fch_act = timezone.now()

            if not articulos:
                messages.error(request, "Debe agregar al menos un producto.")
                return redirect("agregar_ingresos")


            # Guardar entrada
            entrada = TblEntrada.objects.create(
                entrada_fecha=fch_act,  #fch actual,
                entrada_num_doc=entrada_num_doc,
                entrada_subtotal=entrada_subtotal,
                entrada_costo_igv=entrada_monto_igv,
                entrada_igv=entrada_igv,
                entrada_costo_total=entrada_total,
                proveedor_id=proveedor_id,
                tipo_doc_almacen_id=tipo_doc_id,
                usuario_id=request.user.id
            )

            # Guardar detalle por producto
            for art in articulos:
                if art["cantidad"] <= 0 or art["precio"] <= 0:
                    messages.error(request, "Cantidad y precio deben ser mayores a cero.")
                    return redirect("agregar_ingresos")
                
                # Obtener y limpiar series para este artículo específico
                series = request.POST.getlist(f'serie_{art["id"]}[]')
                series = [s.strip().upper() for s in series if s.strip()]

                # Validar cantidad de series
                if len(series) != art["cantidad"]:
                    messages.error(request, f"Debe ingresar {art['cantidad']} series para el producto {art['id']}.")
                    return redirect("agregar_ingresos")
                
                # Validar duplicados en BD
                for serie in series:
                    if TblProductoSerie.objects.filter(prod_ser_serie=serie).exists():
                        messages.error(request, f"La serie '{serie}' ya existe.")
                        return redirect("agregar_ingresos")

                detEntrada = TblDetEntrada.objects.create(
                    entrada=entrada,
                    prod_id=art["id"],
                    det_entrada_cantidad=art["cantidad"],
                    det_entrada_precio_costo=art["precio"],
                    det_entrada_sub_total=art["subtotal"]
                )

                for serie in series:
                    TblProductoSerie.objects.create(
                        prod_ser_serie=serie,
                        prod_ser_estado=1,
                        prod_ser_fecha_sit=fch_act,
                        det_entrada=detEntrada
                    )

                # Llamar al procedimiento almacenado
                with connection.cursor() as cursor:
                    cursor.callproc("sp_actualizar_kardex", [
                        'ENTRADA',
                        art["id"],
                        art["cantidad"],
                        art["precio"],
                        0  # cantidad_salida
                    ])

            messages.success(request, "Entrada registrada correctamente.")
            return redirect("lista_ingresos")  # Puedes cambiar a la vista de listado

        except Exception as e:
            # Marcar rollback si ocurre error
            transaction.set_rollback(True)

            # Extraer mensaje SQL si viene de procedimiento
            mensaje_mysql = str(e)
            if hasattr(e, 'args') and len(e.args) > 1:
                mensaje_mysql = e.args[1]

            messages.error(request, f"Ocurrió un error: {mensaje_mysql}")
            return redirect("agregar_ingresos")

    proveedores = TblProveedor.objects.all()
    tipos_doc = TblTipoDocAlmacen.objects.filter(tipo_doc_almacen_tipo__in=['ES', 'E', 'EI'])
    productos = TblProducto.objects.filter(prod_estado=True)

    numero_documento = request.GET.get('num_doc')

    if numero_documento:
        existeNumDoc = TblEntrada.objects.filter(entrada_num_doc=numero_documento).exists()
        return JsonResponse({'existeNumDoc': existeNumDoc})


    context = {
        'breadcrumbs': [['Ingresos','/lista_ingresos/'],['Registro de nuevo ingreso','']],
        'menu_padre': 'compras',
        'menu_hijo': 'ingresos',
        'proveedores': proveedores,
        'tipos_doc': tipos_doc,
        'productos': productos,
    }

    return render(request, 'tienda/agregar_ingresos.html', context)

@solo_personal
def detalle_ingreso(request, ingreso_id):
    try:
        entrada = get_object_or_404(TblEntrada, pk=ingreso_id)
        detalles = TblDetEntrada.objects.filter(entrada=entrada).select_related('prod')

        context = {
            'breadcrumbs': [['Ingresos','/lista_ingresos/'],['Detalle de compra','']],
            'menu_padre': 'compras',
            'menu_hijo': 'ingresos',
            'entrada': entrada,
            'detalles': detalles,
        }
        return render(request, 'tienda/detalle_ingreso.html', context)
    except Exception as e:
        # Mostrar el error solo en la consola
        print("Error en vista detalle_ingreso:")
        print(traceback.format_exc())
        messages.error(request, f"Ocurrió un error: {str(e)}")
        return redirect("lista_ingresos")

#### CLIENTES ####
@solo_personal
def lista_clientes(request):
    clientes = TblCliente.objects.all()

    context = {
        'breadcrumbs': [['Clientes', '']],
        'menu_padre': 'ventas',
        'menu_hijo': 'clientes',
        'clientes': clientes,
    }

    return render(request, 'tienda/lista_clientes.html', context)

@solo_personal
def verificar_datos_cliente(request):
    numDocClie = request.GET.get('numDocClien')
    emailClie = request.GET.get('emailClien')
    telefClie = request.GET.get('telefo')
    existeDocClie = TblCliente.objects.filter(cliente_nrodocumento=numDocClie).exists() if numDocClie else False
    existeEmailClie = TblCliente.objects.filter(cliente_email=emailClie).exists() if emailClie else False
    existeTelefClie = TblCliente.objects.filter(cliente_telefono=telefClie).exists() if telefClie else False

    return JsonResponse({'existeDocCliente': existeDocClie, 'existsEmailCliente': existeEmailClie, 'existsTelefCliente': existeTelefClie})

def generar_contrasena(longitud=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=longitud))

@solo_personal
def agregar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Obtener datos del formulario
                data = form.cleaned_data
                tipo_documento = data['cliente_tipodocumento']
                documento = data['cliente_nrodocumento']
                nombre = data['cliente_nombre']
                paterno = data['cliente_paterno']
                materno = data['cliente_materno']
                nacimiento = data['cliente_fechanac']
                telefono = data['cliente_telefono']
                correo = data['cliente_email']
                sexo = data['cliente_sexo']
                direccion = data['cliente_direccion']

                # Generar contraseña
                contrasena = generar_contrasena()

                # Obtener tipo de usuario y cargo predeterminado
                tipo_cliente = TblTipoUsuario.objects.get(tipo_usuario_descrip__iexact='cliente')
                cargo_nulo = TblCargo.objects.get(cargo_emp_descrip__iexact='Sin_cargo')

                # Crear usuario
                nuevo_usuario = TblUsuario.objects.create(
                    usuario_tipodocumento=tipo_documento,
                    usuario_nrodocumento=documento,
                    usuario_nombre=nombre,
                    usuario_paterno=paterno,
                    usuario_materno=materno,
                    usuario_direccion=direccion,
                    usuario_fechanac=nacimiento,
                    usuario_sexo=sexo,
                    usuario_email=correo,
                    usuario_cambiopwd=True,
                    cargo=cargo_nulo,
                    tipo_usuario=tipo_cliente,
                    username=documento,
                    password=make_password(contrasena)
                )

                # Crear cliente vinculado
                cliente = TblCliente.objects.create(
                    cliente_tipodocumento=tipo_documento,
                    cliente_nrodocumento=documento,
                    cliente_nombre=nombre,
                    cliente_paterno=paterno,
                    cliente_materno=materno,
                    cliente_fechanac=nacimiento,
                    cliente_telefono=telefono,
                    cliente_email=correo,
                    cliente_sexo=sexo,
                    cliente_direccion=direccion,
                    usuario=nuevo_usuario
                )

                # Enviar correo
                send_mail_api(
                    subject='Bienvenido a Nexus Motos',
                    message=f'Hola {nombre}, ya eres parte de nuestros clientes. Tu usuario es: {documento} y tu contraseña: {contrasena}',
                    recipient_list=[correo],
                )

                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'cliente': {
                            'id': cliente.cliente_id,
                            'nombre': f"{cliente.cliente_nombre} {cliente.cliente_paterno}"
                        }
                    })
                else:
                    return redirect('lista_clientes')
            except Exception as e:
                # Captura cualquier error inesperado al guardar
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'Ocurrió un error al guardar el cliente: ' + str(e)
                    })
                else:
                    messages.error(request, f"Ocurrió un error al guardar el cliente: {str(e)}")
                    context = {
                        'breadcrumbs': [['Clientes','/lista_clientes/'],['Registro de nuevo cliente','']],
                        'menu_padre': 'ventas',
                        'menu_hijo': 'clientes',
                        'form': form,
                    }
                    return render(request, 'tienda/agregar_cliente.html', context)
        else:
            # Si el formulario es inválido
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                html = render_to_string('tienda/agregar_cliente_form.html', {'form': form}, request=request)
                return JsonResponse({'success': False, 'html': html})
    else:
        form = ClienteForm()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html = render_to_string('tienda/agregar_cliente_form.html', {'form': form}, request=request)
            return JsonResponse({'success': False, 'html': html})
    
    context = {
        'breadcrumbs': [['Clientes','/lista_clientes/'],['Registro de nuevo cliente','']],
        'menu_padre': 'ventas',
        'menu_hijo': 'clientes',
        'form': form,
    }

    return render(request, 'tienda/agregar_cliente.html', context)

@solo_personal
def editar_cliente(request, clien_id):
    cliente = get_object_or_404(TblCliente, cliente_id = clien_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)

        if form.is_valid():
            cliente.save()
            return redirect('lista_clientes')
            
        else:
            print(form.errors)
    else:
        form = ClienteForm(instance=cliente)

    context = {
        'breadcrumbs': [['Clientes','/lista_clientes/'],['Edición de cliente','']],
        'menu_padre': 'ventas',
        'menu_hijo': 'clientes',
        'form': form,
        'cliente': cliente,
    }
    return render(request, 'tienda/editar_cliente.html', context)

@solo_personal
def detalle_cliente(request, clien_id):
    cliente = get_object_or_404(TblCliente, pk=clien_id)
    
    context = {
        'breadcrumbs': [['Clientes','/lista_clientes/'],['Detalle de cliente','']],
        'menu_padre': 'ventas',
        'menu_hijo': 'clientes',
        'cliente': cliente,
    }

    return render(request, 'tienda/detalle_cliente.html', context)

#### VENTAS ####
@solo_personal
def lista_ventas(request):
    ventas = (
        TblVenta.objects
        .select_related('cliente', 'usuario', 'metodo_pago')
        .prefetch_related('tblfinanciamiento_set')
        .annotate(
            prioridad=Case(
                When(venta_online=True, venta_online_entregado=False, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by('prioridad', '-venta_fecha_venta')
    )

    ventas_estado = []
    for venta in ventas:
        metodo = venta.metodo_pago.metodo_pago_descrip.lower()
        if metodo == 'efectivo':
            estado = 'PAGADO'
        else:
            financiamientos = venta.tblfinanciamiento_set.all()
            if not financiamientos.exists():
                estado = 'PAGADO'
            elif all(f.financia_estado == 'PAGADO' for f in financiamientos):
                estado = 'PAGADO'
            else:
                estado = 'PEND. DE PAGO'
        
        ventas_estado.append({
            'venta': venta,
            'estado': estado,
        })

    context = {
        'breadcrumbs': [['Ventas', '']],
        'menu_padre': 'ventas',
        'menu_hijo': 'ventas',
        'ventas_estado': ventas_estado,
    }

    return render(request, 'tienda/lista_ventas.html', context)

@require_POST
@solo_personal
def confirmar_entrega_articulo(request, venta_id):
    venta = get_object_or_404(TblVenta, venta_id=venta_id)

    nuevo_estado = not venta.venta_online_entregado
    venta.venta_online_entregado = nuevo_estado
    venta.save()

    # Actualizamos la salida relacionada (si existe)
    TblSalida.objects.filter(venta=venta).update(salida_online_entregado=nuevo_estado)

    return JsonResponse({"message": 'Se ha confirmado la entrega correctamente.'})

@transaction.atomic
@solo_personal
def agregar_venta(request):
    if request.method == 'POST':
        try:
            cliente_id = request.POST.get('cliente')
            tipo_comprobante = request.POST.get('venta_tipo_comprobante')
            nro_documento = request.POST.get('venta_nro_documento')
            metodo_pago_id = request.POST.get('metodo_pago')
            usuario_id = request.user.id

            subtotal = float(request.POST.get('venta_subtotal'))
            igv = float(request.POST.get('igv'))
            costo_igv = float(request.POST.get('venta_igv'))
            total = float(request.POST.get('venta_total'))
            monto_efectivo = float(request.POST.get('monto_efectivo'))

            tipo_doc_obj = TblTipoDocAlmacen.objects.get(tipo_doc_almacen_descripcion=tipo_comprobante)

            fch_act = timezone.now()

            # 1. Guardar TblVenta
            try:
                venta = TblVenta.objects.create(
                    venta_fecha_venta=fch_act,
                    venta_tipo_comprobante=tipo_comprobante,
                    venta_nro_documento=nro_documento,
                    venta_monto_efectivo=monto_efectivo,
                    venta_subtotal=subtotal,
                    venta_igv=igv,
                    venta_costo_igv=costo_igv,
                    venta_total=total,
                    metodo_pago_id=metodo_pago_id,
                    cliente_id=cliente_id,
                    usuario_id=usuario_id
                )
            except Exception as e:
                print("Error al guardar TblVenta:", e)
                raise

            # 2. Guardar TblDetVenta
            try:
                productos_json = request.POST.get('productos_json')
                total_productos = json.loads(productos_json)
                for item in total_productos:
                    TblDetVenta.objects.create(
                        venta=venta,
                        prod_id=item['id'],
                        det_venta_cantidad=item['cantidad'],
                        det_venta_precio_unitario=float(item['precio']),
                        det_venta_subtotal=float(item['costo']),
                        det_venta_dcto=float(item['descuentoT']),
                        det_venta_total=float(item['subtotal'])
                    )
            except Exception as e:
                print("Error al guardar TblDetVenta:", e)
                raise

            # 3. Guardar TblSalida
            try:
                salida = TblSalida.objects.create(
                    salida_fecha=fch_act,
                    salida_num_doc=nro_documento,
                    salida_subtotal=subtotal,
                    salida_igv=igv,
                    salida_costo_igv=costo_igv,
                    salida_costo_total=total,
                    salida_motivo='VENTA',
                    tipo_doc_almacen_id=tipo_doc_obj.tipo_doc_almacen_id,
                    venta=venta,
                    usuario_id=usuario_id
                )
            except Exception as e:
                print("Error al guardar TblSalida:", e)
                raise

            # 4. Guardar TblDetSalida
            try:
                for item in total_productos:
                    cantidad = item['cantidad']
                    subtotal_item = float(item['subtotal'])
                    precio_salida = float(subtotal_item / cantidad if cantidad else 0)

                    # Verificar series disponibles
                    series_disponibles = TblProductoSerie.objects.filter(
                        det_entrada__prod_id=item['id'],
                        prod_ser_estado=1
                    ).order_by('prod_ser_fecha_sit')[:cantidad]

                    if series_disponibles.count() < cantidad:
                        messages.error(request, f"Stock insuficiente para el producto ID {item['id']}.")
                        raise Exception(f"Stock insuficiente para el producto ID {item['id']}.")

                    det_salida = TblDetSalida.objects.create(
                        salida=salida,
                        prod_id=item['id'],
                        det_salida_cantidad=cantidad,
                        det_salida_sub_total=subtotal_item,
                        det_salida_precio_salida=precio_salida
                    )

                    # Actualizar series: cambiar estado, fecha, y asociar det_salida
                    for serie in series_disponibles:
                        serie.prod_ser_estado = 2
                        serie.prod_ser_fecha_sit = fch_act
                        serie.det_salida = det_salida
                        serie.save()
                    
                    # Llamar al procedimiento almacenado
                    with connection.cursor() as cursor:
                        cursor.callproc("sp_actualizar_kardex", [
                            'SALIDA',
                            item["id"],
                            0,
                            0,
                            cantidad  # cantidad_salida
                        ])

            except Exception as e:
                print("Error al guardar TblDetSalida o actualizar series:", e)
                raise

            # 5. Si hay financiamiento
            try:
                metodo_pago_nombre = TblMetodoPago.objects.get(metodo_pago_id=metodo_pago_id).metodo_pago_descrip.lower()
                if metodo_pago_nombre in ['credito', 'mixto']:
                    monto_financiar = float(request.POST.get('monto_financiar', 0))
                    num_cuotas = int(request.POST.get('num_cuotas'))
                    tasa_interes = float(request.POST.get('tasa_interes'))
                    total_interes = float(request.POST.get('total_interes'))
                    total_financiamiento = float(request.POST.get('total_financiamiento'))
                    pago_mensual = float(request.POST.get('pago_mensual'))
                    fecha_pago_opcion = int(request.POST.get('fecha_pago'))

                    financiamiento = TblFinanciamiento.objects.create(
                        financia_monto_financiado=monto_financiar,
                        financia_numero_cuotas=num_cuotas,
                        financia_tasa_interes=tasa_interes,
                        financia_total_interes=total_interes,
                        financia_monto_total=total_financiamiento,
                        financia_fecha_registro=date.today(),
                        financia_estado='PENDIENTE',
                        venta=venta
                    )

                    for i in range(num_cuotas):
                        mes = date.today().month + i + 1
                        año = date.today().year
                        if mes > 12:
                            mes -= 12
                            año += 1
                        fecha_cuota = date(año, mes, fecha_pago_opcion)

                        TblDetFinanciamiento.objects.create(
                            det_finan_num_cuota=i + 1,
                            det_finan_monto_cuota=pago_mensual,
                            det_finan_fch_pago_max=fecha_cuota,
                            det_finan_estado_pago='PENDIENTE',
                            financia=financiamiento
                        )
            except Exception as e:
                print("Error al guardar financiamiento:", e)
                raise    

            messages.success(request, "Venta registrada correctamente.")
            url = reverse('lista_ventas') # vista del listado de ventas
            query_string = urlencode({'pdf': venta.venta_id})
            full_url = f'{url}?{query_string}'
            return redirect(full_url)

        except Exception as e:
            print("ERROR AL GUARDAR VENTA:", e)
            transaction.set_rollback(True)

            # Extraer mensaje SQL si viene de procedimiento
            mensaje_mysql = str(e)
            if hasattr(e, 'args') and len(e.args) > 1:
                mensaje_mysql = e.args[1]

            messages.error(request, f"Ocurrió un error: {mensaje_mysql}")
            return redirect("agregar_venta")
            
    else:
        # Vista GET: cargar formulario
        clientes = TblCliente.objects.all()
        comprobantes = TblTipoDocAlmacen.objects.filter(tipo_doc_almacen_tipo='ES')
        metodos_pago = TblMetodoPago.objects.all()
        productos = TblProducto.objects.filter(prod_estado=True).select_related('tblkardex')
        nro_documento = f"V-{TblVenta.objects.count() + 1:05d}"
        
        tipo_seleccionado_id = request.GET.get('tipo_doc_id')

        if tipo_seleccionado_id:
            tipo_doc = TblTipoDocAlmacen.objects.filter(pk=tipo_seleccionado_id).first()
            if tipo_doc:
                tipo_descrip = tipo_doc.tipo_doc_almacen_descripcion # boleta o factura
            else:
                return JsonResponse({'numero': ''})  # En caso no exista tipo doc.
            
            if tipo_descrip == "Boleta":
                tipo_cod_prefijo = 'B001'
            elif tipo_descrip == 'Factura':
                tipo_cod_prefijo = 'F001'
            else:
                return JsonResponse({'numero': ''})  # En caso de un tipo inesperado
            
            # Obtener las ventas que tienen ese tipo_descrip
            ventas = TblVenta.objects.filter(
                venta_tipo_comprobante=tipo_descrip
            )

            # Extraer el correlativo mayor
            max_num = 0
            for venta in ventas:
                try:
                    num = int(venta.venta_nro_documento.split("-")[1])
                    max_num = max(max_num, num)
                except:
                    continue

            nuevo_num = max_num + 1
            numero_generado = f"{tipo_cod_prefijo}-{nuevo_num:08d}"

            return JsonResponse({'numero': numero_generado})


        context = {
            'breadcrumbs': [['Ventas','/lista_ventas/'],['Registro de nueva venta','']],
            'menu_padre': 'ventas',
            'menu_hijo': 'ventas',
            'clientes': clientes,
            'comprobantes': comprobantes,
            'metodos_pago': metodos_pago,
            'productos': productos,
            'nro_documento': nro_documento
        }
        return render(request, 'tienda/agregar_venta.html', context)

def numero_a_letras(numero):
    parte_entera = int(numero)
    parte_decimal = int(round((numero - parte_entera) * 100))

    texto = num2words(parte_entera, lang='es').upper()
    return f"{texto} Y {parte_decimal:02d}/100 NUEVOS SOLES"

@solo_personal
def generar_pdf_venta(request, venta_id):
    venta = get_object_or_404(TblVenta, pk=venta_id)
    detalle_venta = TblDetVenta.objects.filter(venta=venta).select_related('prod')
    financiamiento = TblFinanciamiento.objects.filter(venta=venta).first()
    detalle_financiamiento = TblDetFinanciamiento.objects.filter(financia=financiamiento) if financiamiento else []

    descuento_total = sum(item.det_venta_dcto for item in detalle_venta)
    total_letras = numero_a_letras(venta.venta_total)
    
    context = {
        'venta': venta,
        'detalle_venta': detalle_venta,
        'financiamiento': financiamiento,
        'detalle_financiamiento': detalle_financiamiento,
        'descuento_total': descuento_total,
        'total_letras': total_letras,
    }

    template_path = 'tienda/venta_pdf.html'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="venta_{venta_id}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)
    
    return response

@solo_personal
def detalle_venta(request, venta_id):
    try:
        venta = get_object_or_404(TblVenta, pk=venta_id)
        detalle_venta = TblDetVenta.objects.filter(venta=venta).select_related('prod')
        financiamiento = TblFinanciamiento.objects.filter(venta=venta).first()
        detalle_financiamiento = TblDetFinanciamiento.objects.filter(financia=financiamiento).order_by('det_finan_fch_pago_max') if financiamiento else []

        # Obtener la primera cuota pendiente
        primera_pend_id = None
        for cuota in detalle_financiamiento:
            if cuota.det_finan_estado_pago=="PENDIENTE" and not cuota.det_finan_comprob_imagen:
                primera_pend_id = cuota.det_finan_id
                break

        descuento_total = sum(item.det_venta_dcto for item in detalle_venta)

        context = {
            'breadcrumbs': [['Ventas','/lista_ventas/'],['Detalle venta','']],
            'menu_padre': 'ventas',
            'menu_hijo': 'ventas',
            'venta': venta,
            'detalle_venta': detalle_venta,
            'financiamiento': financiamiento,
            'detalle_financiamiento': detalle_financiamiento,
            'primera_pend_id': primera_pend_id,
            'descuento_total': descuento_total,
        }
        return render(request, 'tienda/detalle_venta.html', context)
    except Exception as e:
        # Mostrar el error solo en la consola
        print("Error en vista detalle_venta:")
        print(traceback.format_exc())
        messages.error(request, f"Ocurrió un error: {str(e)}")
        return redirect("lista_ventas")

@require_POST
@solo_personal
def registrar_pago(request, cuota_id):
    try:
        cuota = TblDetFinanciamiento.objects.get(pk=cuota_id)
        imagen = request.FILES.get("imagen_pago")

        if imagen:
            extensiones_permitidas = ['.jpg', '.jpeg', '.png']
            nombre_archivo = imagen.name.lower()
            if not any(nombre_archivo.endswith(ext) for ext in extensiones_permitidas):
                return JsonResponse({"status": "error", "message": "Formato de imagen no permitido."}, status=400)

            ruta_destino = os.path.join(settings.BASE_DIR, 'staticfiles', 'tienda', 'img', 'comprobantes')
            os.makedirs(ruta_destino, exist_ok=True)
            path_final = os.path.join(ruta_destino, imagen.name)

            with open(path_final, 'wb+') as destino:
                        for chunk in imagen.chunks():
                            destino.write(chunk)
            
            cuota.det_finan_comprob_imagen = imagen.name  # solo el nombre del archivo
            cuota.det_finan_estado_pago = "PAGADO"
            cuota.det_finan_fch_pago_realiza = date.today()
            cuota.save()

            # Verificar si todas las cuotas están pagadas
            todas_pagadas = not TblDetFinanciamiento.objects.filter(
                financia=cuota.financia,
                det_finan_estado_pago='PENDIENTE',
                det_finan_comprob_imagen__isnull=True
            ).exists()

            if todas_pagadas:
                cuota.financia.financia_estado = "PAGADO"
                cuota.financia.save()
            
            return JsonResponse({"status": "success", "message": "Pago registrado correctamente."})
        else:
            return JsonResponse({"status": "error", "message": "Debe subir una imagen."}, status=400)

    except Exception as e:
        print(traceback.format_exc())
        return JsonResponse({"status": "error", "message": f"Ocurrió un error al registrar el pago: {str(e)}"}, status=500)


#### SALIDAS ####
@solo_personal
def lista_salidas(request):
    salidas = TblSalida.objects.select_related('tipo_doc_almacen', 'usuario').all()

    context = {
        'breadcrumbs': [['Salidas', '']],
        'menu_padre': 'almacen',
        'menu_hijo': 'salidas',
        'salidas': salidas,
    }

    return render(request, 'tienda/lista_salidas.html', context)

@transaction.atomic
@solo_personal
def agregar_salida(request):
    if request.method == "POST":
        try:
            tipo_doc_des = request.POST.get("tipo_doc")
            salida_num_doc = request.POST.get("salida_num_doc")
            salida_igv = float(request.POST.get("salida_igv", 0))
            salida_subtotal = float(request.POST.get("subtotal_salida") or 0)
            salida_monto_igv = float(request.POST.get("montoIgv_salida") or 0)
            salida_total = float(request.POST.get("total_salida") or 0)
            salida_motivo = request.POST.get("salida_motivo")

            articulos_json = request.POST.get("articulos")  # Este es un JSON con los productos
            articulos = json.loads(articulos_json)

            # Buscar el tipo de documento
            tipo_doc_alm = TblTipoDocAlmacen.objects.filter(tipo_doc_almacen_descripcion__iexact=tipo_doc_des).first()
            if not tipo_doc_alm:
                messages.error(request, "No existe tipo documento.")
                return redirect("agregar_salida")
            tipo_doc_id = tipo_doc_alm.tipo_doc_almacen_id

            if not articulos:
                messages.error(request, "Debe agregar al menos un producto.")
                return redirect("agregar_salida")

            for art in articulos:
                if art["cantidad"] <= 0:
                    messages.error(request, "Cantidad debe ser mayor a cero.")
                    return redirect("agregar_salida")
                if art["precio"] < 0:
                    messages.error(request, "Precio deben ser mayor o igual a cero.")
                    return redirect("agregar_salida")

            # Guardar salida
            salida = TblSalida.objects.create(
                salida_fecha=timezone.now(),  #salida_fecha,
                salida_num_doc=salida_num_doc,
                salida_subtotal=salida_subtotal,
                salida_costo_igv=salida_monto_igv,
                salida_igv=salida_igv,
                salida_costo_total=salida_total,
                salida_motivo=salida_motivo,
                tipo_doc_almacen_id=tipo_doc_id,
                usuario_id=request.user.id
            )

            # Guardar detalle por producto
            for art in articulos:
                TblDetSalida.objects.create(
                    salida=salida,
                    prod_id=art["id"],
                    det_salida_cantidad=art["cantidad"],
                    det_salida_precio_salida=art["precio"],
                    det_salida_sub_total=art["subtotal"]
                )

                # Llamar al procedimiento almacenado
                with connection.cursor() as cursor:
                    cursor.callproc("sp_actualizar_kardex", [
                        'SALIDA',
                        art["id"],
                        0,
                        0,
                        art["cantidad"]  # cantidad_salida
                    ])

            messages.success(request, "Salida registrada correctamente.")
            return redirect("lista_salidas")  # Ccambia a la vista de listado

        except Exception as e:
            # Marcar rollback si ocurre error
            transaction.set_rollback(True)

            # Extraer mensaje SQL si viene de procedimiento
            mensaje_mysql = str(e)
            if hasattr(e, 'args') and len(e.args) > 1:
                mensaje_mysql = e.args[1]

            messages.error(request, f"Ocurrió un error: {mensaje_mysql}")
            return redirect("agregar_salida")

    tipo_doc = TblTipoDocAlmacen.objects.filter(tipo_doc_almacen_tipo='SI').first()
    if tipo_doc:
        tipo_doc_des=tipo_doc.tipo_doc_almacen_descripcion
    else:
        tipo_doc_des = 'Salida interna'
    productos = TblProducto.objects.filter(prod_estado=True).select_related('tblkardex')
    # Obtener las salidas que tienen ese tipo_cod_prefijo
    salidas = TblSalida.objects.filter(tipo_doc_almacen__tipo_doc_almacen_tipo='SI')
    nro_documento = f"SI-{salidas.count() + 1:05d}"
    
    context = {
        'breadcrumbs': [['Salidas','/lista_salidas/'],['Registro de nueva salida','']],
        'menu_padre': 'almacen',
        'menu_hijo': 'salidas',
        'tipo_doc_des': tipo_doc_des,
        'productos': productos,
        'nro_documento': nro_documento,
    }

    return render(request, 'tienda/agregar_salida.html', context)

#### REPORTES ####
@solo_personal
def reporte_compras(request):
    proveedores = TblProveedor.objects.all()
    almacenistas = TblUsuario.objects.filter(cargo__cargo_emp_descrip='Administrador') # el administrador es el que registra las compras
    
    context = {
        'breadcrumbs': [['Reporte compras', '']],
        'menu_padre': 'reportes',
        'menu_hijo': 'reporte_compras',
        'proveedores': proveedores,
        'almacenistas': almacenistas,
    }

    return render(request, 'tienda/reporte_compras.html', context)

@solo_personal
def filtrar_compras(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    proveedor_id = request.GET.get('proveedor')
    usuario_id = request.GET.get('usuario')

    # Validar que si se proporciona una fecha, estén ambas
    if (fecha_inicio and not fecha_fin) or (fecha_fin and not fecha_inicio):
        return JsonResponse({'error': 'Debe seleccionar un rango de fechas completo.'}, status=400)

    filtros = Q()
    if fecha_inicio and fecha_fin:
        fi = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        ff = datetime.strptime(fecha_fin, '%Y-%m-%d')
        filtros &= Q(entrada_fecha__date__range=[fi, ff])
    if proveedor_id != "":
        filtros &= Q(proveedor_id=proveedor_id)
    if usuario_id != "":
        filtros &= Q(usuario_id=usuario_id)

    compras = TblEntrada.objects.filter(filtros).select_related('usuario', 'proveedor', 'tipo_doc_almacen')

    data = []
    for c in compras:
        data.append({
            'fecha': c.entrada_fecha.strftime('%Y-%m-%d'),
            'usuario': c.usuario.usuario_nombre,
            'proveedor': c.proveedor.proveedor_nombre,
            'tipo_doc': c.tipo_doc_almacen.tipo_doc_almacen_descripcion,
            'numero_doc': c.entrada_num_doc,
            'costo_total': float(c.entrada_costo_total),
            'igv': float(c.entrada_igv)
        })

    return JsonResponse({'compras': data})

@solo_personal
def reporte_salidas(request):
    clientes = TblCliente.objects.all()
    almacenistas = TblUsuario.objects.filter(cargo__cargo_emp_descrip='Almacenero')
    
    context = {
        'breadcrumbs': [['Reporte salidas', '']],
        'menu_padre': 'reportes',
        'menu_hijo': 'reporte_salidas',
        'clientes': clientes,
        'almacenistas': almacenistas,
    }

    return render(request, 'tienda/reporte_salidas.html', context)

@solo_personal
def filtrar_salidas(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    usuario_id = request.GET.get('usuario')

    # Validar que si se proporciona una fecha, estén ambas
    if (fecha_inicio and not fecha_fin) or (fecha_fin and not fecha_inicio):
        return JsonResponse({'error': 'Debe seleccionar un rango de fechas completo.'}, status=400)

    filtros = Q()
    if fecha_inicio and fecha_fin:
        fi = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        ff = datetime.strptime(fecha_fin, '%Y-%m-%d')
        filtros &= Q(salida_fecha__date__range=[fi, ff])
    if usuario_id != "":
        filtros &= Q(usuario_id=usuario_id)

    salidas = TblSalida.objects.filter(filtros).select_related('usuario', 'tipo_doc_almacen')

    data = []
    for c in salidas:
        data.append({
            'fecha': c.salida_fecha.strftime('%Y-%m-%d'),
            'usuario': c.usuario.usuario_nombre,
            'tipo_doc': c.tipo_doc_almacen.tipo_doc_almacen_descripcion,
            'numero_doc': c.salida_num_doc,
            'motivo': c.salida_motivo,
            'costo_total': float(c.salida_costo_total),
            'total_igv': float(c.salida_costo_igv)
        })

    return JsonResponse({'salidas': data})

@solo_personal
def reporte_mov_productos(request):
    try:
        productos = TblProducto.objects.filter(tbldetentrada__isnull=False).distinct()
        context = {
            'breadcrumbs': [['Reportes', '']],
            'menu_padre': 'reportes',
            'menu_hijo': 'reporte_mov_productos',
            'productos': productos,
        }

        return render(request, 'tienda/reporte_mov_productos.html', context)
    except Exception as e:
        # Mostrar el error solo en la consola
        print("Error en vista reporte:")
        print(traceback.format_exc())
        messages.error(request, f"Ocurrió un error: {str(e)}")
        return redirect("home")

def buscar_movimientos(request):
    if request.method == 'POST':
        data = []
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        producto_id = request.POST.get('producto_id')

        print(fecha_inicio)
        print(fecha_fin)
        print(producto_id)

        filtro_fecha = Q()
        if fecha_inicio:
            filtro_fecha &= Q(det_entrada__entrada__entrada_fecha__gte=fecha_inicio) | Q(det_salida__salida__salida_fecha__gte=fecha_inicio)
        if fecha_fin:
            filtro_fecha &= Q(det_entrada__entrada__entrada_fecha__lte=fecha_fin) | Q(det_salida__salida__salida_fecha__lte=fecha_fin)

        productos = TblProducto.objects.filter(tbldetentrada__isnull=False).distinct()
        print(productos)
        
        if producto_id and producto_id != '0':
            productos = productos.filter(prod_id=producto_id)

        for producto in productos:
            print(producto)
            movimientos = []

            # ENTRADAS
            entradas = TblDetEntrada.objects.filter(prod_id=producto)
            if fecha_inicio:
                entradas = entradas.filter(entrada__entrada_fecha__date__gte=fecha_inicio)
            if fecha_fin:
                entradas = entradas.filter(entrada__entrada_fecha__date__lte=fecha_fin)

            print(entradas)
            for e in entradas:
                print(e.entrada.entrada_fecha)
                movimientos.append({
                    'fecha_mov': e.entrada.entrada_fecha,
                    'tipo_mov': 'ENTRADA',
                    'tipo_doc': e.entrada.tipo_doc_almacen.tipo_doc_almacen_descripcion,
                    'num_doc': e.entrada.entrada_num_doc,
                    'cant_entrada': e.det_entrada_cantidad,
                    'precio_entrada': float(e.det_entrada_precio_costo),
                    'cant_salida': 0,
                    'precio_salida': 0,
                })

            print(movimientos)

            # SALIDAS
            salidas = TblDetSalida.objects.filter(prod_id=producto)
            if fecha_inicio:
                salidas = salidas.filter(salida__salida_fecha__date__gte=fecha_inicio)
            if fecha_fin:
                salidas = salidas.filter(salida__salida_fecha__date__lte=fecha_fin)

            for s in salidas:
                movimientos.append({
                    'fecha_mov': s.salida.salida_fecha,
                    'tipo_mov': 'SALIDA',
                    'tipo_doc': s.salida.tipo_doc_almacen.tipo_doc_almacen_descripcion,
                    'num_doc': s.salida.salida_num_doc,
                    'cant_entrada': 0,
                    'precio_entrada': 0,
                    'cant_salida': s.det_salida_cantidad,
                    'precio_salida': float(s.det_salida_precio_salida),
                })

            print(movimientos)
            # Ordenamos todos los movimientos por fecha
            movimientos.sort(key=lambda x: x['fecha_mov'])

            # Cálculo del stock acumulado
            saldo = 0
            movimientos_final = []
            for mov in movimientos:
                saldo += mov['cant_entrada'] - mov['cant_salida']
                movimientos_final.append({
                    'producto_modelo': producto.prod_modelo,
                    'producto_marca': producto.prod_marca,
                    'fecha_mov': mov['fecha_mov'].strftime('%Y-%m-%d %H:%M'),
                    'tipo_mov': mov['tipo_mov'],
                    'tipo_doc': mov['tipo_doc'],
                    'num_doc': mov['num_doc'],
                    'cant_entrada': mov['cant_entrada'] if mov['cant_entrada'] != 0 else '',
                    'precio_entrada': mov['precio_entrada'] if mov['cant_entrada'] != 0 else '',
                    'cant_salida': mov['cant_salida'] if mov['cant_salida'] != 0 else '',
                    'precio_salida': mov['precio_salida'] if mov['cant_salida'] != 0 else '',
                    'saldo': saldo
                })

            data.append({'producto': f"{producto.prod_modelo} - {producto.prod_marca}", 'movimientos': movimientos_final})

        return JsonResponse({'data': data})

@solo_personal
def reporte_series_productos(request):
    productos = TblProducto.objects.filter(
        tbldetentrada__isnull=False
    ).distinct()

    context = {
        'breadcrumbs': [['Reportes', '']],
        'menu_padre': 'reportes',
        'menu_hijo': 'reporte_series_productos',
        'productos': productos,
    }

    return render(request, 'tienda/reporte_series_productos.html', context)

def buscar_series_productos(request):
    if request.method == 'POST':
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        producto_id = request.POST.get('producto_id')

        series = TblProductoSerie.objects.select_related(
            'det_entrada__entrada',
            'det_entrada__prod',
            'det_entrada__entrada__tipo_doc_almacen',
            'det_salida__salida',
            'det_salida__salida__tipo_doc_almacen',
        )

        # Filtro por producto si no es '0'
        if producto_id and producto_id != '0':
            series = series.filter(det_entrada__prod__prod_id=producto_id)

        # Filtro por fechas
        if fecha_inicio:
            series = series.filter(det_entrada__entrada__entrada_fecha__date__gte=fecha_inicio)
        if fecha_fin:
            series = series.filter(det_entrada__entrada__entrada_fecha__date__lte=fecha_fin)

        # Ordenar por fecha de entrada, luego por fecha de cambio de estado
        series = series.order_by('det_entrada__entrada__entrada_fecha', 'prod_ser_fecha_sit')

        datos = []
        productos_agregados = set()

        for serie in series:
            prod = serie.det_entrada.prod

            # Fila separadora solo si es un nuevo producto
            if prod.prod_id not in productos_agregados:
                datos.append({
                    'separador': True,
                    'producto': f"{prod.prod_nombre} - {prod.prod_modelo} - {prod.prod_marca}",
                    'serie': '',
                    'situacion': '',
                    'fecha_entrada': '',
                    'num_doc_entrada': '',
                    'tipo_doc_entrada': '',
                    'fecha_salida': '',
                    'num_doc_salida': '',
                    'tipo_doc_salida': '',
                })
                productos_agregados.add(prod.prod_id)

            # Fila de serie
            datos.append({
                'separador': False,
                'serie': serie.prod_ser_serie,
                'situacion': serie.prod_ser_estado,
                'fecha_entrada': serie.det_entrada.entrada.entrada_fecha.strftime('%Y-%m-%d %H:%M'),
                'num_doc_entrada': serie.det_entrada.entrada.entrada_num_doc,
                'tipo_doc_entrada': serie.det_entrada.entrada.tipo_doc_almacen.tipo_doc_almacen_descripcion,
                'fecha_salida': serie.det_salida.salida.salida_fecha.strftime('%Y-%m-%d %H:%M') if serie.det_salida else '',
                'num_doc_salida': serie.det_salida.salida.salida_num_doc if serie.det_salida else '',
                'tipo_doc_salida': serie.det_salida.salida.tipo_doc_almacen.tipo_doc_almacen_descripcion if serie.det_salida else '',
            })

        return JsonResponse({'datos': datos})

@solo_personal
def reporte_productos(request):
    productos = TblProducto.objects.filter(tblkardex__isnull=False).select_related('tblkardex')

    for producto in productos:
        producto.descuento_porcentaje = int(producto.prod_porcenta_dcto or 0)
        producto.stock_actual = producto.tblkardex.kardex_stock_actual
        producto.precio_vigente = float(producto.tblkardex.kardex_precio_vigente or 0)*1.2

    context = {
        'breadcrumbs': [['reportes', '']],
        'menu_padre': 'reportes',
        'menu_hijo': 'reporte_productos',
        'productos': productos,
    }

    return render(request, 'tienda/reporte_productos.html', context)