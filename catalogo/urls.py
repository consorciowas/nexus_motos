from django.urls import path
from . import views

urlpatterns = [
    #path('', views.catalogo_productos, name='catalogo_productos'),
    #path('producto/<int:prod_id>/', views.detalle_catalogo, name='detalle_catalogo'),
    path('registro/', views.registro_cliente, name='registro_cliente'),
    path('registro/validar-documento/', views.validar_documento_cliente, name='validar_documento'),
    path('registro/validar-email/', views.validar_email_cliente, name='validar_email'),
    path('cambiar-contrasena/', views.cambiar_contrasena, name='cambiar_contrasena'),
    path('inicio/', views.inicio, name='inicio'),
    path('motos/', views.catalogo_motos, name='catalogo_motos'),
    path('motos/busqueda/', views.busqueda_motos, name='busqueda_motos'),
    path("moto/<int:prod_id>/", views.detalle_moto, name="detalle_moto"),
    path("moto/<int:prod_id>/cotizar/", views.cotizar_moto, name="cotizar_moto"),
    path("enviar-cotizacion/", views.enviar_cotizacion, name="enviar_cotizacion"),
    path('accesorios/', views.catalogo_accesorios, name='catalogo_accesorios'),
    path('accesorios/busqueda/', views.busqueda_accesorios, name='busqueda_accesorios'),
    path("accesorio/<int:prod_id>/", views.detalle_accesorio, name="detalle_accesorio"),
    path("accesorio/agregar-a-carrito/", views.agregar_a_carrito, name="agregar_a_carrito"),
    path("carrito/", views.vista_carrito, name="vista_carrito"),
    path('carrito/eliminar/', views.eliminar_producto_carrito, name='eliminar_producto_carrito'),
    path('carrito/cambiar-cantidad/', views.cambiar_cantidad_carrito, name='cambiar_cantidad_carrito'),
]