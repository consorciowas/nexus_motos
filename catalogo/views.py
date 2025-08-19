from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from tienda.models import TblProducto, TblKardex, TblUsuario, TblCliente, TblTipoUsuario, TblCargo, TblProductoTalla
from django.db.models import Q
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.urls import reverse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
from django.contrib.auth import logout
from functools import wraps
import random
import string
import os
import json
import traceback
import mercadopago

def logout_no_cliente(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            tipo = getattr(request.user.tipo_usuario, 'tipo_usuario_descrip', '').upper()
            if tipo != 'CLIENTE':
                logout(request)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@logout_no_cliente
def inicio(request):
    """
    Renderiza la página de inicio del catálogo.
    """
    return render(request, 'catalogo/inicio.html')

def validar_documento_cliente(request):
    documento = request.GET.get('documento')
    existe = TblCliente.objects.filter(cliente_nrodocumento=documento).exists()
    return JsonResponse({'existe': existe})

def validar_email_cliente(request):
    email = request.GET.get('email')
    existeEmail = TblCliente.objects.filter(cliente_email=email).exists() if email else False

    return JsonResponse({'existeEmail': existeEmail})


def registro_cliente(request):
    # Generar contraseña aleatoria
    def generar_contrasena():
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        paterno = request.POST.get('paterno')
        materno = request.POST.get('materno')
        correo = request.POST.get('correo')
        telefono = request.POST.get('telefono')
        tipo_documento = request.POST.get('tipo_documento')
        documento = request.POST.get('documento')
        direccion = request.POST.get('direccion')
        nacimiento = request.POST.get('nacimiento')
        sexo = request.POST.get('sexo')
        contrasena = generar_contrasena()

        try:
            # Obtener tipo de usuario y cargo predeterminado para clientes
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
            TblCliente.objects.create(
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
            send_mail(
                subject='Bienvenido a Nexus Motos',
                message=f'Hola {nombre}, ya eres parte de nuestros clientes. Tu usuario es: {documento} y tu contraseña: {contrasena}',
                from_email=settings.EMAIL_HOST_USER,  # configurado en settings
                recipient_list=[correo],
                fail_silently=False
            )

            return JsonResponse({'mensaje': f'Se le envió su usuario y contraseña al correo {correo}'})

        except Exception as e:
            return JsonResponse({'error': f'Ocurrió un error: {str(e)}'}, status=500)

    return render(request, 'catalogo/registro_cliente.html')

@login_required
def cambiar_contrasena(request):
    if request.method == 'POST':
        nueva = request.POST.get('nueva')
        confirmar = request.POST.get('confirmar')

        if nueva != confirmar:
            return JsonResponse({'error': 'Las contraseñas no coinciden'}, status=400)

        user = request.user
        user.password = make_password(nueva)
        user.usuario_cambiopwd = False
        user.save()

        # Mantener sesión activa tras cambiar password
        update_session_auth_hash(request, user)
        
        tipo_usuario = user.tipo_usuario.tipo_usuario_descrip.lower()
        return JsonResponse({
            'mensaje': 'Contraseña modificada correctamente',
            'redirect_url': reverse('inicio' if tipo_usuario == 'cliente' else 'home')
        })

    return render(request, 'catalogo/cambiar_contrasena.html')

def catalogo_productos(request):
    try:
        productos = TblProducto.objects.filter(prod_estado=True)
        return render(request, 'catalogo/catalogo_productos.html', {'productos': productos})
    except Exception as e:
        print("ERROR:", str(e))
        return HttpResponse("Ocurrió un error: " + str(e))

def detalle_catalogo(request, prod_id):
    try:
        producto = get_object_or_404(TblProducto, prod_id=prod_id, prod_estado=True)
        return render(request, 'catalogo/detalle_catalogo.html', {'producto': producto})
    except Exception as e:
        return HttpResponse(f"Error al cargar producto: {e}")

#### CATALOGO MOTOS ####
@logout_no_cliente
def catalogo_motos(request):
    return render(request, 'catalogo/catalogo_motos.html')

def busqueda_motos(request):
    filtros = Q()
    
    marcas = request.GET.getlist('marca')
    categorias = request.GET.getlist('categoria')
    motores = request.GET.getlist('motor')
    precio_max = request.GET.get('precio_max')
    
    if marcas:
        filtros &= Q(prod_marca__in=marcas)
    if categorias:
        filtros &= Q(prod_categoria__in=categorias)
    if motores:
        filtros &= Q(prod_motor__in=motores)
    if precio_max:
        filtros &= Q(tblkardex__kardex_precio_vigente__lte=precio_max)

    try:
        productos = TblProducto.objects.filter(filtros, prod_tipo='MOTO', prod_estado=True).select_related('tblkardex')
    except Exception as e:
        # Mostrar el error solo en la consola
        print("Error:")
        print(str(e))
    
    data = []
    for p in productos:
        data.append({
            'id': p.prod_id,
            'nombre': p.prod_nombre,
            'modelo': p.prod_modelo,
            'motor': p.prod_motor,
            'marca': p.prod_marca,
            'categoria': p.prod_categoria,
            'precio': float(p.tblkardex.kardex_precio_vigente),
            'imagen': p.prod_imagen  # asegúrate que sea URL accesible (usa MEDIA_URL si necesario)
        })
    
    return JsonResponse({'productos': data})

def detalle_moto(request, prod_id):
    producto = TblProducto.objects.get(prod_id=prod_id)
    try:
        kardex = TblKardex.objects.get(prod=producto)
        precio = kardex.kardex_precio_vigente
    except TblKardex.DoesNotExist:
        kardex = None
        precio = None
    
    relacionados = TblProducto.objects.filter(
        prod_categoria=producto.prod_categoria,
        tblkardex__isnull=False
    ).exclude(prod_id=prod_id).select_related('tblkardex')[:5]

    return render(request, "catalogo/detalle_moto.html", {
        "producto": producto,
        "precio": precio,
        "relacionados": relacionados,
    })

def cotizar_moto(request, prod_id):
    try:
        producto = TblProducto.objects.get(prod_id=prod_id)
    except TblProducto.DoesNotExist:
        #return render(request, "404.html", status=404)
        print("Error: Producto no existe")

    return render(request, "catalogo/cotizar_moto.html", {
        "producto": producto,
    })

def fetch_resources(uri, rel):
    """
    Convierte rutas relativas a rutas absolutas para que xhtml2pdf pueda acceder a archivos estáticos (como imágenes).
    """
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        return path
    return uri

def enviar_cotizacion(request):
    if request.method == 'POST':
        nombres = request.POST.get('nombres')
        apellidos = request.POST.get('apellidos')
        documento = request.POST.get('nro_documento')
        tipo_documento = request.POST.get('tipo_documento')
        email = request.POST.get('email')
        telefono = request.POST.get('telefono')
        producto_id = request.POST.get('producto_id')

        try:
            producto = TblProducto.objects.get(prod_id=producto_id)
            kardex = TblKardex.objects.filter(prod=producto).first() #TblKardex.objects.filter(prod=producto).order_by('-kardex_id').first()

            if not kardex:
                return JsonResponse({'error': 'No se encontró el precio del producto.'})
            
            ruta_logo = os.path.join(settings.BASE_DIR, 'staticfiles', 'assets', 'img', 'logos', 'Nexus_2.png')

            context = {
                'nombre_completo': f"{nombres} {apellidos}",
                'documento': documento,
                'tipo_documento': tipo_documento,
                'email': email,
                'telefono': telefono,
                'producto': producto,
                'precio': "{:.2f}".format(kardex.kardex_precio_vigente),
                'fecha': timezone.now().strftime("%d de %B de %Y"),
                'cotizacion_id': "20250717-1201",  # Generar dinámicamente si se desea
                'ruta_logo': ruta_logo.replace('\\', '/'),  # en Windows convierte \ a /
            }

            html = render_to_string("catalogo/cotizacion_pdf.html", context)
            result = BytesIO()
            #pdf = pisa.CreatePDF(html, dest=result)
            pdf = pisa.CreatePDF(html, dest=result, link_callback=fetch_resources)

            if not pdf.err:
                email_message = EmailMessage(
                    'Cotización Nexus Motos',
                    'Adjunto encontrará su cotización en PDF.',
                    settings.EMAIL_HOST_USER,
                    [email]
                )
                email_message.attach('cotizacion.pdf', result.getvalue(), 'application/pdf')
                email_message.send()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'error': 'Error al generar el PDF.'})

        except TblProducto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado.'})
        except Exception as e:
            return JsonResponse({'error': str(e)})

    return JsonResponse({'error': 'Método no permitido'})

#### CATALOGO ACCESORIOS ####
@logout_no_cliente
def catalogo_accesorios(request):
    return render(request, 'catalogo/catalogo_accesorios.html')

def busqueda_accesorios(request):
    filtros = Q()
    
    categorias = request.GET.getlist('categoria')
    marcas = request.GET.getlist('marca')
    precio_max = request.GET.get('precio_max')
    
    if categorias:
        filtros &= Q(prod_codigo__in=categorias)
    if marcas:
        filtros &= Q(prod_marca__in=marcas)
    if precio_max:
        filtros &= Q(tblkardex__kardex_precio_vigente__lte=precio_max)

    try:
        productos = TblProducto.objects.filter(filtros, prod_tipo='ACCESORIO', prod_estado=True).select_related('tblkardex')
    except Exception as e:
        # Mostrar el error solo en la consola
        print("Error:")
        print(str(e))
    
    data = []
    for p in productos:
        data.append({
            'id': p.prod_id,
            'nombre': p.prod_nombre,
            'modelo': p.prod_modelo,
            'tono': p.prod_tono,
            'marca': p.prod_marca,
            'categoria': p.prod_categoria,
            'precio': float(p.tblkardex.kardex_precio_vigente),
            'imagen': p.prod_imagen  # asegúrate que sea URL accesible (usa MEDIA_URL si necesario)
        })
    
    return JsonResponse({'productos': data})

def detalle_accesorio(request, prod_id):
    producto = TblProducto.objects.get(prod_id=prod_id)

    try:
        kardex = TblKardex.objects.get(prod=producto)
        stock_actual = int(kardex.kardex_stock_actual or 0)
        precio = kardex.kardex_precio_vigente
    except TblKardex.DoesNotExist:
        stock_actual = 0
        precio = None

    tallas = TblProductoTalla.objects.filter(prod=producto)

    # Verificar si ya está en el carrito y ajustar stock disponible
    carrito = request.session.get('carrito', {})
    cantidades_en_carrito = {}

    for key, item in carrito.items():
        # clave puede ser "prodid" o "prodid_talla"
        pid_session = str(item.get('prod_id') or str(key).split('_')[0])
        if str(prod_id) != pid_session:
            continue

        talla_item = (item.get('talla') or '')
        cantidades_en_carrito[talla_item] = cantidades_en_carrito.get(talla_item, 0) + int(item.get('cantidad', 0))

    en_carrito = cantidades_en_carrito.get('', 0)

    if not tallas.exists():
        stock_disponible = max(0, stock_actual - en_carrito)
    else:
        stock_disponible = None
        for talla in tallas:
            cant_carrito_talla = cantidades_en_carrito.get(talla.prod_talla_codigo, 0)
            talla.en_carrito = cant_carrito_talla
            talla.stock_disponible = max(0, int(talla.prod_talla_stock or 0) - cant_carrito_talla)

    relacionados = TblProducto.objects.filter(
        prod_codigo=producto.prod_codigo,
        tblkardex__isnull=False
    ).exclude(prod_id=prod_id).select_related('tblkardex')[:5]

    return render(request, "catalogo/detalle_accesorio.html", {
        "producto": producto,
        "precio": precio,
        "stock_actual": stock_actual,
        "stock_disponible": stock_disponible,     # solo sin tallas
        "en_carrito": en_carrito,                 # solo sin tallas
        "tallas": tallas,                         # cada talla trae .stock_disponible y .en_carrito
        "relacionados": relacionados,
    })

@require_POST
def agregar_a_carrito(request):
    data = json.loads(request.body)

    prod_id = int(data['prod_id'])
    prod_marca = data.get('prod_marca', '')
    prod_codigo = data.get('prod_codigo', '')
    prod_modelo = data.get('prod_modelo', '')
    prod_tono = data.get('prod_tono', '')
    prod_imagen = data.get('prod_imagen', '')
    talla = (data.get('talla') or '').strip()  # código de talla, si aplica
    cantidad = int(data.get('cantidad', 1))

    # 1) Obtener producto y precio/stock desde BD
    producto = get_object_or_404(TblProducto, prod_id=prod_id)

    precio = 0.0
    stock_db = 0

    try:
        kardex = TblKardex.objects.get(prod=producto)
        precio = float(kardex.kardex_precio_vigente or 0)
        stock_db = int(kardex.kardex_stock_actual or 0)
    except TblKardex.DoesNotExist:
        # Si no hay kardex, queda stock_db = 0
        pass

    # Si hay talla, el stock real es el de esa talla
    if talla:
        talla_obj = get_object_or_404(
            TblProductoTalla,
            prod=producto,
            prod_talla_codigo=talla
        )
        stock_db = int(talla_obj.prod_talla_stock or 0)

    # 2) Leer carrito de SESSION
    carrito = request.session.get('carrito', {})

    # clave de item - estructura: "prodId_talla" o "prodId"
    key = f"{prod_id}_{talla}" if talla else str(prod_id)

    cantidad_en_carrito = 0
    if key in carrito:
        cantidad_en_carrito = int(carrito[key].get('cantidad', 0))

    disponible = max(0, stock_db - cantidad_en_carrito)
    if cantidad > disponible:
        # No permitir pasarse del stock disponible real
        return JsonResponse({
            'success': False,
            'mensaje': f'Stock insuficiente. {disponible} disponibles.'
        })

    # 3) Agregar/actualizar item en carrito
    if key in carrito:
        carrito[key]['cantidad'] = cantidad_en_carrito + cantidad
        carrito[key]['stock'] = stock_db         # guardamos referencia de stock actual
        carrito[key]['precio'] = precio          # mantenemos precio vigente
    else:
        carrito[key] = {
            'prod_id': prod_id,                  # útil para la vista detalle
            'marca': prod_marca,
            'codigo': prod_codigo,
            'modelo': prod_modelo,
            'tono': prod_tono,
            'precio': precio,
            'imagen': prod_imagen,
            'stock': stock_db,
            'cantidad': cantidad,
            'talla': talla
        }

    request.session['carrito'] = carrito
    request.session.modified = True

    total_items = sum(int(item['cantidad']) for item in carrito.values())
    request.session['carrito_total'] = total_items

    return JsonResponse({
        'success': True,
        'producto': carrito[key],
        'total_items': total_items
    })

def _stock_actual_item(item):
    """
    Devuelve el stock actual desde BD para el item del carrito.
    Si trae talla -> stock por talla. Si no, stock del kardex.
    """
    prod_id = int(item.get('prod_id', 0) or 0)
    talla = (item.get('talla') or '').strip()

    try:
        producto = TblProducto.objects.get(prod_id=prod_id)
    except TblProducto.DoesNotExist:
        return 0

    if talla:
        talla_obj = TblProductoTalla.objects.filter(
            prod=producto, prod_talla_codigo=talla
        ).first()
        return int(talla_obj.prod_talla_stock or 0) if talla_obj else 0

    kardex = TblKardex.objects.filter(prod=producto).first()
    return int(kardex.kardex_stock_actual or 0) if kardex else 0


def _estado_item(cantidad, stock):
    """
    Retorna uno de: 'agotado', 'excede', 'igual', 'ok'
    Según las casuísticas.
    """
    if stock <= 0:
        return 'agotado'
    if cantidad > stock:
        return 'excede'
    if cantidad == stock:
        return 'igual'
    return 'ok'


def _recalcular_resumen_y_bloqueo(carrito):
    """
    Recalcula total, cantidad_total, total_items (para el badge),
    y si el checkout debe bloquearse (algún item excede o está agotado).
    """
    total = 0.0
    cantidad_total = 0
    bloqueo_checkout = False

    for it in carrito.values():
        cant = int(it.get('cantidad', 0) or 0)
        precio = float(it.get('precio', 0) or 0)
        total += cant * precio
        cantidad_total += cant

        stock_db = _stock_actual_item(it)
        estado = _estado_item(cant, stock_db)
        if estado in ('agotado', 'excede'):
            bloqueo_checkout = True

    total_items = cantidad_total
    return total, cantidad_total, total_items, bloqueo_checkout


def vista_carrito(request):
    carrito = request.session.get('carrito', {})

    productos = []
    bloqueo_checkout = False
    total = 0.0
    cantidad_total = 0

    for key, item in carrito.items():
        stock_db = _stock_actual_item(item)
        cantidad = int(item.get('cantidad', 0) or 0)
        precio = float(item.get('precio', 0) or 0)
        subtotal = cantidad * precio
        estado = _estado_item(cantidad, stock_db)

        if estado in ('agotado', 'excede'):
            bloqueo_checkout = True

        productos.append({
            'key': key,
            'prod_id': item.get('prod_id'),
            'codigo': item.get('codigo'),
            'marca': item.get('marca'),
            'modelo': item.get('modelo'),
            'tono': item.get('tono'),
            'talla': item.get('talla') or None,
            'precio': precio,
            'cantidad': cantidad,
            'imagen': item.get('imagen'),
            'stock': stock_db,
            'estado': estado,
            'subtotal': subtotal,
        })

        total += subtotal
        cantidad_total += cantidad

    return render(request, 'catalogo/carrito.html', {
        'productos': productos,
        'total': total,
        'cantidad_total': cantidad_total,
        'bloqueo_checkout': bloqueo_checkout,
        'MP_PUBLIC_KEY': settings.MP_PUBLIC_KEY,
    })


@require_POST
def cambiar_cantidad_carrito(request):
    """
    Cambia la cantidad de un ítem: delta = +1 o -1.
    Aplica límites: mínimo 1, máximo stock actual.
    Actualiza sesión, devuelve UI state, totales y bloqueo checkout.
    """
    try:
        data = json.loads(request.body)
        key = data.get('key')
        delta = int(data.get('delta', 0) or 0)

        carrito = request.session.get('carrito', {})
        if key not in carrito:
            return JsonResponse({'success': False, 'mensaje': 'Producto no encontrado en el carrito'})

        item = carrito[key]
        stock_db = _stock_actual_item(item)
        cantidad_actual = int(item.get('cantidad', 0) or 0)

        # Caso stock 0: no se puede sumar ni restar (quedan deshabilitados)
        if stock_db <= 0:
            estado = 'agotado'
            # no cambiamos cantidad; invitamos a eliminar
            total, cantidad_total, total_items, bloqueo = _recalcular_resumen_y_bloqueo(carrito)
            return JsonResponse({
                'success': True,
                'item': {
                    'key': key,
                    'cantidad': cantidad_actual,
                    'stock': stock_db,
                    'estado': estado,
                    'subtotal': cantidad_actual * float(item.get('precio', 0) or 0)
                },
                'resumen': {
                    'total': total,
                    'cantidad_total': cantidad_total,
                    'bloqueo_checkout': bloqueo
                },
                'total_items': total_items
            })

        # Aplicar delta con límites
        nueva_cantidad = cantidad_actual + delta
        if nueva_cantidad < 1:
            nueva_cantidad = 1
        if nueva_cantidad > stock_db:
            nueva_cantidad = stock_db

        item['cantidad'] = nueva_cantidad
        carrito[key] = item
        request.session['carrito'] = carrito
        request.session.modified = True

        # Recalcular resumen y bloqueo
        total, cantidad_total, total_items, bloqueo = _recalcular_resumen_y_bloqueo(carrito)

        # También guardamos el total de items para el badge global
        request.session['carrito_total'] = total_items

        estado = _estado_item(nueva_cantidad, stock_db)

        return JsonResponse({
            'success': True,
            'item': {
                'key': key,
                'cantidad': nueva_cantidad,
                'stock': stock_db,
                'estado': estado,
                'subtotal': nueva_cantidad * float(item.get('precio', 0) or 0)
            },
            'resumen': {
                'total': total,
                'cantidad_total': cantidad_total,
                'bloqueo_checkout': bloqueo
            },
            'total_items': total_items
        })
    except Exception as e:
        return JsonResponse({'success': False, 'mensaje': str(e)})


@require_POST
def eliminar_producto_carrito(request):
    try:
        data = json.loads(request.body)
        key = data.get('key')

        carrito = request.session.get('carrito', {})

        if key in carrito:
            del carrito[key]
            request.session['carrito'] = carrito
            request.session.modified = True

            total, cantidad_total, total_items, bloqueo = _recalcular_resumen_y_bloqueo(carrito)

            # También guardamos el total de items para el badge global
            request.session['carrito_total'] = total_items

            return JsonResponse({
                'success': True,
                'total_items': total_items,
                'resumen': {
                    'total': total,
                    'cantidad_total': cantidad_total,
                    'bloqueo_checkout': bloqueo
                }
            })
        else:
            return JsonResponse({'success': False, 'mensaje': 'Producto no encontrado en el carrito'})
    except Exception as e:
        return JsonResponse({'success': False, 'mensaje': str(e)})
    
def crear_preferencia(request):
    if request.method == "POST":
        try:
            # SDK Mercado Pago
            sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

            carrito = request.session.get("carrito", [])

            if not carrito:
                return JsonResponse({"error": "El carrito está vacío"}, status=400)

            items = []
            for producto in carrito.values():
                items.append({
                    "title": producto["codigo"],
                    "description": f"{producto['marca']} {producto['modelo']} {producto['tono']}",
                    "quantity": int(producto["cantidad"]),
                    "unit_price": float(producto["precio"]),
                    "currency_id": "PEN"
                })

            
            preference_data = {
                "items": items,
                "back_urls": {
                    "success": request.build_absolute_uri(reverse("pago_exito")),
                    "failure": request.build_absolute_uri(reverse("pago_error")),
                    "pending": request.build_absolute_uri(reverse("pago_pendiente"))
                },
                "auto_return": "approved",
                "payment_methods": {
                    "installments": 1 #,  # Solo 1 cuota
                    #"excluded_payment_types": [{"id": "ticket"}]  # Excluir pagos en efectivo
                }
            }

            print("Back URLs:", request.build_absolute_uri(reverse("pago_exito")))

            preference_response = sdk.preference().create(preference_data)
            print("RESPUESTA MP:", preference_response)  # Para debug en consola

            if "response" not in preference_response or "id" not in preference_response["response"]:
                return JsonResponse({"error": "No se pudo crear la preferencia"}, status=500)

            preference = preference_response["response"]

            print(preference)

            return JsonResponse({"id": preference["id"]})

        except Exception as e:
            print("ERROR creando preferencia:", e)
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)
    
def pago_exito(request):
    return render(request, "catalogo/pago_exito.html")

def pago_error(request):
    return render(request, "catalogo/pago_error.html")

def pago_pendiente(request):
    return render(request, "catalogo/pago_pendiente.html")