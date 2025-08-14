const swiper = new Swiper(".mySwiper", {
  slidesPerView: 1,
  spaceBetween: 15,
  pagination: {
    el: ".swiper-pagination",
    clickable: true,
  },
  navigation: {
    nextEl: ".swiper-button-next",
    prevEl: ".swiper-button-prev",
  },
  breakpoints: {
    576: { slidesPerView: 2 },
    768: { slidesPerView: 3 },
    992: { slidesPerView: 4 },
  },
});

let tallaSeleccionada = null;
let stockDisponible = parseInt(document.getElementById("spanStockActual")?.dataset.stockDisponible || 0, 10) || 0;

const btnAumentar = document.getElementById('btn-aumentar');
const btnDisminuir = document.getElementById('btn-disminuir');
const inputCantidad = document.getElementById('cantidad');
const btnAgregarCar = document.getElementById('btn-agregar-carrito');
const alertAgregarCarrito = document.getElementById('alert-agregar-carrito');
const spanStockActual = document.getElementById('spanStockActual');
const tallasDisponibles = document.querySelectorAll('.btn-talla');

function actualizarUIStock() {
  const totalEnCarrito = parseInt(btnAgregarCar.dataset.enCarrito || 0, 10);

  // Si hay tallas y no se ha seleccionado ninguna
  if (tallasDisponibles.length > 0 && !tallaSeleccionada) {
    spanStockActual.innerText = `Seleccione una talla`;
    inputCantidad.value = 0;
    btnAumentar.disabled = true;
    btnDisminuir.disabled = true;
    btnAgregarCar.disabled = true;
    alertAgregarCarrito.innerText = '';
    return;
  }

  if (stockDisponible <= 0) {
    spanStockActual.innerText = `Agotado`;
    inputCantidad.value = 0;
    btnAumentar.disabled = true;
    btnDisminuir.disabled = true;
    btnAgregarCar.disabled = true;

    if (totalEnCarrito > 0) {
      alertAgregarCarrito.innerHTML = `<i class="bx bx-error-circle text-warning"></i> ${totalEnCarrito} disponibles en tu carrito`;
    }
  } else {
    spanStockActual.innerText = `${stockDisponible} disponibles`;
    inputCantidad.value = 1;
    btnDisminuir.disabled = true;
    btnAumentar.disabled = stockDisponible <= 1;
    btnAgregarCar.disabled = false;
    alertAgregarCarrito.innerText = '';
  }
}

function actualizarBotones(cantidad) {
  btnDisminuir.disabled = cantidad <= 1;
  btnAumentar.disabled = cantidad >= stockDisponible;
}

btnAumentar.addEventListener('click', function () {
  let cantidad = parseInt(inputCantidad.value, 10);
  if (cantidad < stockDisponible) {
    cantidad++;
    inputCantidad.value = cantidad;
    actualizarBotones(cantidad);
  }
});

btnDisminuir.addEventListener('click', function () {
  let cantidad = parseInt(inputCantidad.value, 10);
  if (cantidad > 1) {
    cantidad--;
    inputCantidad.value = cantidad;
    actualizarBotones(cantidad);
  }
});

function agregarACarrito(prodId, talla, cantidad) {
  btnAgregarCar.disabled = true;
  btnAgregarCar.innerHTML = `
    <span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
    Agregando...
  `;

  const prodMarca = document.getElementById("prodMarca").value;
  const prodCodigo = document.getElementById("prodCodigo").value;
  const prodModelo = document.getElementById("prodModelo").value;
  const prodTono = document.getElementById("prodTono").value;
  const prodPrecio = document.getElementById("prodPrecio").value;
  const prodImagen = document.getElementById("prodImagen").value;

  fetch('/catalogo/accesorio/agregar-a-carrito/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': CSRF_TOKEN
    },
    body: JSON.stringify({
      prod_id: prodId,
      prod_marca: prodMarca,
      prod_codigo: prodCodigo,
      prod_modelo: prodModelo,
      prod_tono: prodTono,
      prod_precio: prodPrecio,
      prod_imagen: prodImagen,
      stock_actual: stockDisponible,
      talla: talla,
      cantidad: cantidad
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      // 1️⃣ Actualizar stock antes de mostrar modal
      stockDisponible -= cantidad;

      // 2️⃣ Actualizar dataset de stock en el HTML
      spanStockActual.dataset.stockDisponible = stockDisponible;

      // 3️⃣ Actualizar su dataset enCarrito para evitar stock viejo
      if (tallaSeleccionada) {
        // 🔹 Con tallas
        const optionTalla = document.querySelector(`[data-talla="${tallaSeleccionada}"]`);
        if (optionTalla) {
          optionTalla.dataset.stockDisponible = stockDisponible;

          // 🔹 Guardar también cuántas unidades hay en carrito para esa talla
          const enCarrito = parseInt(optionTalla.dataset.enCarrito || 0, 10) + cantidad;
          optionTalla.dataset.enCarrito = enCarrito;
          btnAgregarCar.dataset.enCarrito = enCarrito;
        }
      } else {
        // 🔹 Sin tallas
        const enCarrito = parseInt(btnAgregarCar.dataset.enCarrito || 0, 10) + cantidad;
        btnAgregarCar.dataset.enCarrito = enCarrito;
      }

      mostrarModalConfirmacion(data.producto);
      actualizarCantidadCarrito(data.total_items);
      actualizarUIStock();
    } else {
      alertAgregarCarrito.innerHTML = `<i class="bx bx-error-circle text-warning"></i> ${data.mensaje}`;
    }
  })
  .finally(() => {
    //btnAgregarCar.disabled = false;
    btnAgregarCar.innerHTML = 'Agregar a carrito';
  });
}

function actualizarCantidadCarrito(total) {
  document.getElementById('contador-carrito').innerText = total;
}

function mostrarModalConfirmacion(producto) {
  const { codigo, marca, modelo, tono, precio, imagen, stock, cantidad, talla } = producto;
  let descripcion = `${codigo} ${marca} ${modelo} ${tono}`;
  if (talla) descripcion += `, ${talla}`;

  const precioFormateado = `S/. ${parseFloat(precio || 0).toFixed(2)}`;

  document.getElementById('prodConfImagen').src = `${STATIC_URL_IMG}${imagen}`;
  document.getElementById('prodConfMarca').textContent = marca;
  document.getElementById('prodConfDescrip').textContent = descripcion;
  document.getElementById('prodConfPrecio').textContent = precioFormateado;
  document.getElementById('prodConfCant').value = cantidad;
  document.getElementById('prodConfStock').textContent = stockDisponible > 0 
    ? `Máximo ${stockDisponible} unidades.` 
    : `Has alcanzado la cantidad máxima para este producto.`;

  new bootstrap.Modal(document.getElementById('modalConfirmacion')).show();
}

tallasDisponibles.forEach(btn => {
  btn.addEventListener('click', function () {
    tallaSeleccionada = this.dataset.talla;
    stockDisponible = parseInt(this.dataset.stockDisponible, 10) || 0;

    tallasDisponibles.forEach(b => b.classList.remove('active'));
    this.classList.add('active');

    // Actualizar dataset del botón de agregar para reflejar stock en carrito
    btnAgregarCar.dataset.enCarrito = this.dataset.enCarrito || 0;

    actualizarUIStock();
  });
});

btnAgregarCar.addEventListener('click', function () {
  alertAgregarCarrito.innerText = '';
  const prodId = this.dataset.prodId;
  const cantTallas = parseInt(this.dataset.cantTallas, 10);
  const cantidad = parseInt(inputCantidad.value, 10);

  if (cantTallas > 0 && (!tallaSeleccionada)) {
    alertAgregarCarrito.innerHTML = `<i class="bx bx-error-circle text-warning"></i> Seleccione una talla`;
    return;
  }
  if (stockDisponible <= 0) {
    alertAgregarCarrito.innerHTML = `<i class="bx bx-error-circle text-warning"></i> Stock insuficiente`;
    return;
  }
  agregarACarrito(prodId, tallaSeleccionada, cantidad);
});

document.addEventListener('DOMContentLoaded', actualizarUIStock);