from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class TblCargo(models.Model):
    cargo_id = models.AutoField(primary_key=True)
    cargo_emp_descrip = models.CharField(max_length=45)

    class Meta:
        managed = False
        db_table = 'tbl_cargo'

    def __str__(self):
        return self.cargo_emp_descrip

class TblCliente(models.Model):
    cliente_id = models.AutoField(primary_key=True)
    cliente_nrodocumento = models.CharField(max_length=45)
    cliente_tipodocumento = models.CharField(max_length=45)
    cliente_nombre = models.CharField(max_length=45)
    cliente_paterno = models.CharField(max_length=45)
    cliente_materno = models.CharField(max_length=45)
    cliente_fechanac = models.DateField()
    cliente_telefono = models.CharField(max_length=45)
    cliente_email = models.CharField(max_length=45, blank=True, null=True)
    cliente_sexo = models.CharField(max_length=45, blank=True, null=True)
    cliente_direccion = models.CharField(max_length=245, blank=True, null=True)
    cliente_fecha = models.DateTimeField(default=timezone.now)
    usuario = models.OneToOneField('TblUsuario', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'tbl_cliente'


class TblDetEntrada(models.Model):
    det_entrada_id = models.AutoField(primary_key=True)
    det_entrada_cantidad = models.IntegerField()
    det_entrada_precio_costo = models.DecimalField(max_digits=8, decimal_places=2)
    det_entrada_sub_total = models.DecimalField(max_digits=8, decimal_places=2)
    entrada = models.ForeignKey('TblEntrada', models.DO_NOTHING)
    prod = models.ForeignKey('TblProducto', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_det_entrada'


class TblDetFinanciamiento(models.Model):
    det_finan_id = models.AutoField(primary_key=True)
    det_finan_num_cuota = models.IntegerField()
    det_finan_monto_cuota = models.DecimalField(max_digits=7, decimal_places=2)
    det_finan_fch_pago_max = models.DateField()
    det_finan_fch_pago_realiza = models.DateField(blank=True, null=True)
    det_finan_estado_pago = models.CharField(max_length=9)
    det_finan_comprob_imagen = models.CharField(max_length=255, blank=True, null=True)
    financia = models.ForeignKey('TblFinanciamiento', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_det_financiamiento'


class TblDetSalida(models.Model):
    det_salida_id = models.AutoField(primary_key=True)
    det_salida_cantidad = models.IntegerField(blank=True, null=True)
    det_salida_precio_salida = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    det_salida_sub_total = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    prod = models.ForeignKey('TblProducto', models.DO_NOTHING)
    salida = models.ForeignKey('TblSalida', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_det_salida'


class TblDetVenta(models.Model):
    det_venta_id = models.AutoField(primary_key=True)
    det_venta_cantidad = models.IntegerField()
    det_venta_precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    det_venta_subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    det_venta_dcto = models.DecimalField(max_digits=8, decimal_places=2)
    det_venta_total = models.DecimalField(max_digits=8, decimal_places=2)
    prod = models.ForeignKey('TblProducto', models.DO_NOTHING)
    venta = models.ForeignKey('TblVenta', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_det_venta'


class TblEntrada(models.Model):
    entrada_id = models.AutoField(primary_key=True)
    entrada_fecha = models.DateTimeField()
    entrada_subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    entrada_costo_igv = models.DecimalField(max_digits=8, decimal_places=2)
    entrada_igv = models.DecimalField(max_digits=8, decimal_places=2)
    entrada_costo_total = models.DecimalField(max_digits=8, decimal_places=2)
    entrada_num_doc = models.CharField(max_length=45)
    proveedor = models.ForeignKey('TblProveedor', models.DO_NOTHING)
    tipo_doc_almacen = models.ForeignKey('TblTipoDocAlmacen', models.DO_NOTHING)
    usuario = models.ForeignKey('TblUsuario', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_entrada'


class TblFinanciamiento(models.Model):
    financia_id = models.AutoField(primary_key=True)
    financia_monto_financiado = models.DecimalField(max_digits=7, decimal_places=2)
    financia_numero_cuotas = models.IntegerField()
    financia_tasa_interes = models.DecimalField(max_digits=4, decimal_places=2)
    financia_total_interes = models.DecimalField(max_digits=7, decimal_places=2)
    financia_monto_total = models.DecimalField(max_digits=7, decimal_places=2)
    financia_fecha_registro = models.DateField()
    financia_estado = models.CharField(max_length=9)
    venta = models.ForeignKey('TblVenta', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_financiamiento'


class TblKardex(models.Model):
    kardex_fecha_mov = models.DateTimeField()
    kardex_cantidad_total_entrada = models.IntegerField(blank=True, null=True)
    kardex_ultimo_precio_entrada = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    kardex_cantidad_total_salida = models.IntegerField(blank=True, null=True)
    kardex_ultimo_precio_salida = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)  # Field renamed to remove unsuitable characters.
    kardex_stock_actual = models.IntegerField()
    kardex_precio_vigente = models.DecimalField(max_digits=7, decimal_places=2)
    kardex_costo_total_saldo = models.DecimalField(max_digits=8, decimal_places=2)
    kardex_stock_minimo = models.IntegerField()
    kardex_porcentaje_utilidad = models.DecimalField(max_digits=5, decimal_places=2)
    prod = models.OneToOneField('TblProducto', models.DO_NOTHING, primary_key=True)

    class Meta:
        managed = False
        db_table = 'tbl_kardex'


class TblMetodoPago(models.Model):
    metodo_pago_id = models.AutoField(primary_key=True)
    metodo_pago_descrip = models.CharField(max_length=45)

    class Meta:
        managed = False
        db_table = 'tbl_metodo_pago'


class TblProducto(models.Model):
    prod_id = models.AutoField(primary_key=True)
    prod_tipo = models.CharField(max_length=45)
    prod_codigo = models.CharField(max_length=45)
    prod_nombre = models.CharField(max_length=25)
    prod_modelo = models.CharField(max_length=45)
    prod_motor = models.CharField(max_length=10, blank=True, null=True)
    prod_categoria = models.CharField(max_length=45, blank=True, null=True)
    prod_marca = models.CharField(max_length=45)
    prod_aniofabricacion = models.CharField(max_length=10, blank=True, null=True)
    prod_cilindrada = models.CharField(max_length=6, blank=True, null=True)
    prod_potencia = models.CharField(max_length=10, blank=True, null=True)
    prod_freno_delantero = models.CharField(max_length=200, blank=True, null=True)
    prod_freno_posterior = models.CharField(max_length=200, blank=True, null=True)
    prod_neumatico_delantero = models.CharField(max_length=45, blank=True, null=True)
    prod_neumatico_posterior = models.CharField(max_length=45, blank=True, null=True)
    prod_suspension_delantera = models.CharField(max_length=145, blank=True, null=True)
    prod_suspension_posterior = models.CharField(max_length=145, blank=True, null=True)
    prod_rendimiento_galon = models.CharField(max_length=10, blank=True, null=True)
    prod_tono = models.CharField(max_length=45, blank=True, null=True)
    prod_certificacion = models.CharField(max_length=100, blank=True, null=True)
    prod_visor = models.CharField(max_length=145, blank=True, null=True)
    prod_calota_externa = models.CharField(max_length=45, blank=True, null=True)
    prod_calota_interna = models.CharField(max_length=45, blank=True, null=True)
    prod_ventilacion = models.CharField(max_length=145, blank=True, null=True)
    prod_almohadilla = models.CharField(max_length=145, blank=True, null=True)
    prod_hebilla = models.CharField(max_length=45, blank=True, null=True)
    prod_material = models.CharField(max_length=145, blank=True, null=True)
    prod_proteccion = models.CharField(max_length=145, blank=True, null=True)
    prod_cierre = models.CharField(max_length=145, blank=True, null=True)
    prod_medidas = models.CharField(max_length=145, blank=True, null=True)
    prod_descripcion = models.TextField(blank=True, null=True)
    prod_fecha_registro = models.DateTimeField()
    prod_porcenta_dcto = models.DecimalField(max_digits=4, decimal_places=2, blank=True, default=0)
    prod_estado = models.BooleanField(default=True)
    prod_imagen = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'tbl_producto'


class TblProductoSerie(models.Model):
    prod_ser_id = models.AutoField(primary_key=True)
    prod_ser_serie = models.CharField(max_length=40)
    prod_ser_estado = models.IntegerField()
    prod_ser_fecha_sit = models.DateTimeField()
    det_entrada = models.ForeignKey('TblDetEntrada', models.DO_NOTHING)
    det_salida = models.ForeignKey('TblDetSalida', models.DO_NOTHING, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'tbl_producto_serie'


class TblProductoImagen(models.Model):
    prod_img_id = models.AutoField(primary_key=True)
    prod_img_nombre = models.CharField(max_length=255)
    prod = models.ForeignKey('TblProducto', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_producto_imagen'


class TblProductoTalla(models.Model):
    prod_talla_id = models.AutoField(primary_key=True)
    prod_talla_codigo = models.CharField(max_length=5)
    prod_talla_stock = models.IntegerField()
    prod = models.ForeignKey('TblProducto', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_producto_talla'
        unique_together = ('prod', 'prod_talla_codigo')  # No repetir la misma talla para el mismo producto


class TblProveedor(models.Model):
    proveedor_id = models.AutoField(primary_key=True)
    proveedor_nombre = models.CharField(max_length=100)
    proveedor_ruc = models.CharField(max_length=45)
    proveedor_telefono = models.CharField(max_length=45)
    proveedor_direccion = models.CharField(max_length=255)
    proveedor_email = models.CharField(max_length=255)
    proveedor_fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'tbl_proveedor'


class TblSalida(models.Model):
    salida_id = models.AutoField(primary_key=True)
    salida_fecha = models.DateTimeField()
    salida_subtotal = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    salida_costo_igv = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    salida_igv = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    salida_costo_total = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    salida_num_doc = models.CharField(max_length=45)
    salida_motivo = models.CharField(max_length=200, blank=True, null=True)
    salida_eliminado = models.BooleanField(default=False)
    tipo_doc_almacen = models.ForeignKey('TblTipoDocAlmacen', models.DO_NOTHING)
    venta = models.ForeignKey('TblVenta', models.DO_NOTHING, null=True, blank=True)
    usuario = models.ForeignKey('TblUsuario', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_salida'


class TblTipoDocAlmacen(models.Model):
    tipo_doc_almacen_id = models.AutoField(primary_key=True)
    tipo_doc_almacen_descripcion = models.CharField(max_length=45)
    tipo_doc_almacen_tipo = models.CharField(max_length=45)

    class Meta:
        managed = False
        db_table = 'tbl_tipo_doc_almacen'


class TblTipoUsuario(models.Model):
    tipo_usuario_id = models.AutoField(primary_key=True)
    tipo_usuario_descrip = models.CharField(max_length=45)

    class Meta:
        managed = False
        db_table = 'tbl_tipo_usuario'

    def __str__(self):
        return self.tipo_usuario_descrip

class TblUsuario(AbstractUser):
    id = models.AutoField(primary_key=True, db_column='usuario_id')
    username = models.CharField(max_length=150, unique=True, verbose_name='Nombre de usuario', db_column='usuario_nombreusuario')
    password = models.CharField(max_length=255, verbose_name='Contraseña', db_column='usuario_password')  # <- Aquí lo conectas

    last_login = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)

    usuario_nrodocumento = models.CharField(max_length=45)
    usuario_tipodocumento = models.CharField(max_length=45)
    usuario_nombre = models.CharField(max_length=45)
    usuario_paterno = models.CharField(max_length=45)
    usuario_materno = models.CharField(max_length=45)
    usuario_fechanac = models.DateField()
    usuario_email = models.CharField(max_length=255)
    usuario_sexo = models.CharField(max_length=45)
    usuario_direccion = models.CharField(max_length=255)
    usuario_cambiopwd = models.BooleanField(default=False)
    tipo_usuario = models.ForeignKey('TblTipoUsuario', on_delete=models.DO_NOTHING)
    cargo = models.ForeignKey('TblCargo', on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'tbl_usuario'
        managed = False 

    def __str__(self):
        return self.username


class TblVenta(models.Model):
    venta_id = models.AutoField(primary_key=True)
    venta_fecha_venta = models.DateTimeField()
    venta_tipo_comprobante = models.CharField(max_length=7)
    venta_monto_efectivo = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    venta_subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    venta_costo_igv = models.DecimalField(max_digits=8, decimal_places=2)
    venta_igv = models.DecimalField(max_digits=8, decimal_places=2)
    venta_total = models.DecimalField(max_digits=8, decimal_places=2)
    venta_nro_documento = models.CharField(max_length=45)
    venta_cliente_ruc = models.CharField(max_length=45, blank=True, null=True)
    venta_cliente_ruc_razon_social = models.CharField(max_length=245, blank=True, null=True)
    venta_cliente_ruc_direccion = models.CharField(max_length=245, blank=True, null=True)
    venta_cliente_ruc_telefono = models.CharField(max_length=45, blank=True, null=True)
    venta_cliente_ruc_correo = models.CharField(max_length=245, blank=True, null=True)
    venta_eliminado = models.BooleanField(default=False)
    cliente = models.ForeignKey(TblCliente, models.DO_NOTHING)
    usuario = models.ForeignKey(TblUsuario, models.DO_NOTHING)
    metodo_pago = models.ForeignKey(TblMetodoPago, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tbl_venta'