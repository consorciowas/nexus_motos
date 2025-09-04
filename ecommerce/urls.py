"""
URL configuration for ecommerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from tienda import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # API REST
    path('app/', include('app.urls')),

    # HOME---------
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path("api/dashboard/overview/", views.api_dashboard_overview, name="api_dashboard_overview"),
    path("api/dashboard/state/", views.api_dashboard_state, name="api_dashboard_state"),
    path("api/dashboard/filter/", views.api_dashboard_filter, name="api_dashboard_filter"),
    path('login/', views.login_view, name='login'),
    path('recuperar_cuenta/', views.recuperar_cuenta, name='recuperar_cuenta'),
    # path('logout/',views.signoup, name= 'logout'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    
    # ARTICULOS-------------------
    path('lista_articulos/',views.lista_articulos, name= 'lista_articulos'),
    path('agregar_articulos/',views.agregar_articulos, name= 'agregar_articulos'),
    path('articulo/<int:producto_id>/', views.detalle_articulo, name='detalle_articulo'),
    path('editar_articulo/<int:producto_id>/', views.editar_articulo, name='editar_articulo'),
    path('cambiar_estado_articulo/<int:producto_id>/', views.cambiar_estado_articulo, name='cambiar_estado_articulo'),
    # INGRESOS-------------------
    path('lista_ingresos/',views.lista_ingresos, name= 'lista_ingresos'),
    path('agregar_ingresos/',views.agregar_ingresos, name= 'agregar_ingresos'),
    path('validar_serie/', views.validar_serie, name='validar_serie'),
    path('ingreso/<int:ingreso_id>/', views.detalle_ingreso, name='detalle_ingreso'),
    # PROVEEDOR-------------------
    path('lista_proveedores/',views.lista_proveedores, name= 'lista_proveedores'),
    path('agregar_proveedor/',views.agregar_proveedor, name= 'agregar_proveedor'),
    path('proveedor/<int:prov_id>/', views.detalle_proveedor, name='detalle_proveedor'),
    path('editar_proveedor/<int:prov_id>/', views.editar_proveedor, name='editar_proveedor'),
    # CLIENTES-------------------
    path('lista_clientes/',views.lista_clientes, name= 'lista_clientes'),
    path('agregar_cliente/',views.agregar_cliente, name= 'agregar_cliente'),
    path('cliente/<int:clien_id>/', views.detalle_cliente, name='detalle_cliente'),
    path('editar_cliente/<int:clien_id>/', views.editar_cliente, name='editar_cliente'),
    # VENTAS-------------------
    path('lista_ventas/',views.lista_ventas, name= 'lista_ventas'),
    path('lista_ventas/confirmar_entrega/<int:venta_id>/', views.confirmar_entrega_articulo, name='confirmar_entrega_articulo'),
    path('agregar_venta/',views.agregar_venta, name= 'agregar_venta'),
    path('venta/pdf/<int:venta_id>/', views.generar_pdf_venta, name='generar_pdf_venta'),
    path('venta/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    path('venta/registrar_pago/<int:cuota_id>/', views.registrar_pago, name='registrar_pago'),
    # SALIDAS-------------------
    path('lista_salidas/',views.lista_salidas, name= 'lista_salidas'),
    path('agregar_salida/',views.agregar_salida, name= 'agregar_salida'),
    # USUARIO-------------------
    path('lista_usuarios/',views.lista_usuarios, name= 'lista_usuarios'),
    path('agregar_usuario/',views.agregar_usuario, name= 'agregar_usuario'),
    path('usuario/<int:id>/', views.detalle_usuario, name='detalle_usuario'),
    path('editar_usuario/<int:id>/', views.editar_usuario, name='editar_usuario'),
    # VALIDACIONES
    path('registrar/api/consultar-dni/', views.consultar_dni, name='consultar_dni'),
    path('registrar/verificar-username/', views.verificar_username, name='verificar_username'),
    path('registrar/verificar-datos-bd/', views.verificar_datos, name='verificar_datos'),
    path('registrar/verificar-datos-cliente-bd/', views.verificar_datos_cliente, name='verificar_datos_cliente'),
    path('verificar-articulo-existe/', views.verificar_articulo_existe, name='verificar_articulo'),
    path('verificar-proveedor/', views.verificar_proveedor, name='verificar_proveedor'),
    #REPORTES-----------
    path('reporte_compras/', views.reporte_compras, name='reporte_compras'),
    path('filtrar-compras/', views.filtrar_compras, name='filtrar_compras'),
    path('reporte_salidas/', views.reporte_salidas, name='reporte_salidas'),
    path('filtrar-salidas/', views.filtrar_salidas, name='filtrar_salidas'),
    path('reporte_mov_productos/', views.reporte_mov_productos, name='reporte_mov_productos'),
    path('buscar_movimientos/', views.buscar_movimientos, name='buscar_movimientos'),
    path('reporte_series_productos/', views.reporte_series_productos, name='reporte_series_productos'),
    path('buscar_series_productos/', views.buscar_series_productos, name='buscar_series_productos'),
    path('reporte_productos/', views.reporte_productos, name='reporte_productos'),
    #CATALOGO-------------
    path('catalogo/', include('catalogo.urls')),

]
