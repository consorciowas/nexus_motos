function mostrarSpinner() {
    document.getElementById('overlay-spinner').style.display = 'flex';
}

function ocultarSpinner() {
    document.getElementById('overlay-spinner').style.display = 'none';
}

function qs(el, sel) { return el.querySelector(sel); }
function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

function setCheckoutBlock(bloquear) {
  const btn = document.getElementById('btn-checkout');
  const alertBox = document.getElementById('alerta-checkout');
  if (!btn || !alertBox) return;

  btn.disabled = !!bloquear;
  alertBox.classList.toggle('d-none', !bloquear);
}

function renderResumen(resumen, totalItems) {
  if (resumen) {
    const carCant = document.getElementById('carro-cant');
    const cant = document.getElementById('resumen-cant');
    const sub = document.getElementById('resumen-subtotal');
    const tot = document.getElementById('resumen-total');
    if (carCant) carCant.textContent = resumen.cantidad_total;
    if (cant) cant.textContent = resumen.cantidad_total;
    if (sub) sub.textContent = Number(resumen.total).toFixed(2);
    if (tot) tot.textContent = Number(resumen.total).toFixed(2);
    setCheckoutBlock(resumen.bloqueo_checkout);
  }
  // badge global del carrito (si existe en tu layout)
  const badge = document.getElementById('contador-carrito');
  if (badge && typeof totalItems !== 'undefined') {
    badge.textContent = totalItems;
  }
}

function aplicarEstadoFila(row, estado, stock, cantidad) {
  // datasets
  row.dataset.estado = estado;
  row.dataset.stock = stock;
  row.dataset.cantidad = cantidad;

  // elementos
  const btnMenos = qs(row, '.btn-menos');
  const btnMas = qs(row, '.btn-mas');
  const spanCant = qs(row, '.cantidad');
  const label = qs(row, '.max-label');
  const btnEliminar = qs(row, '.btn-eliminar');

  // cantidad visible
  if (spanCant) spanCant.textContent = cantidad;

  // defaults
  let labelText = '';
  let labelIsAlert = false;
  let minusDisabled = (cantidad <= 1);
  let plusDisabled = false;

  if (stock <= 0) {
    // Casuística 4
    labelText = 'Agotado';
    labelIsAlert = true;
    minusDisabled = true;
    plusDisabled = true;
    if (btnEliminar) btnEliminar.classList.add('btn-eliminar-alerta');
  } else if (cantidad > stock) {
    // Casuística 3
    labelText = `Máx ${stock} unidades`;
    labelIsAlert = true;
    plusDisabled = true;
    if (btnEliminar) btnEliminar.classList.remove('btn-eliminar-alerta');
  } else if (cantidad === stock) {
    // Casuística 2
    labelText = `Máx ${stock} unidades`;
    labelIsAlert = true;
    plusDisabled = true;
    if (btnEliminar) btnEliminar.classList.remove('btn-eliminar-alerta');
  } else {
    // Casuística 1
    labelText = `Máx ${stock} unidades`;
    labelIsAlert = false;
    plusDisabled = false;
    if (btnEliminar) btnEliminar.classList.remove('btn-eliminar-alerta');
  }

  // aplicar en DOM
  if (btnMenos) btnMenos.disabled = minusDisabled;
  if (btnMas) btnMas.disabled = plusDisabled;
  if (label) {
    label.textContent = labelText;
    label.classList.toggle('estado-alerta', labelIsAlert);
    label.classList.toggle('estado-max', !labelIsAlert);
  }
}

function cambiarCantidad(row, delta) {
  const key = row.dataset.key;

  mostrarSpinner();

  fetch('/catalogo/carrito/cambiar-cantidad/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': CSRF_TOKEN
    },
    body: JSON.stringify({ key, delta })
  })
  .then(r => r.json())
  .then(data => {
    if (!data.success) {
      alert(data.mensaje || 'No se pudo actualizar la cantidad.');
      return;
    }

    const it = data.item;
    aplicarEstadoFila(row, it.estado, parseInt(it.stock || 0, 10), parseInt(it.cantidad || 1, 10));

    // Actualizar resumen / badge
    renderResumen(data.resumen, data.total_items);

    // Si por efecto del cambio un producto queda fuera de reglas (no debería),
    // el bloqueo_checkout viene actualizado desde el servidor.
  })
  .catch(error => {
    console.error("Error:", error);
  })
  .finally(() => {
    ocultarSpinner();
  });
}

function eliminarProducto(row) {
  const key = row.dataset.key;

  mostrarSpinner();

  fetch('/catalogo/carrito/eliminar/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': CSRF_TOKEN
    },
    body: JSON.stringify({ key })
  })
  .then(r => r.json())
  .then(data => {
    if (!data.success) {
      alert(data.mensaje || 'No se pudo eliminar el producto.');
      return;
    }

    // Eliminar del DOM
    row.remove();

    // Si no quedan productos, reemplaza la vista
    const cont = document.getElementById('carrito-contenido');
    if (cont && data.total_items === 0) {
      cont.innerHTML = `
        <div class="text-center py-5">
          <h4 class="text-secondary fw-bold">Tu Carrito está vacío</h4>
        </div>`;
    }

    // Actualizar resumen/badge
    renderResumen(data.resumen, data.total_items);
  })
  .catch(error => {
    console.error("Error:", error);
  })
  .finally(() => {
    ocultarSpinner();
  });
}

// Listeners
document.addEventListener('DOMContentLoaded', () => {
  const filas = qsa('.producto-carrito');

  // Inicializar estado visual de cada fila desde datasets renderizados por Django
  filas.forEach(row => {
    const stock = parseInt(row.dataset.stock || 0, 10);
    const cantidad = parseInt(row.dataset.cantidad || 1, 10);
    const estado = row.dataset.estado || 'ok';
    aplicarEstadoFila(row, estado, stock, cantidad);

    const btnMas = qs(row, '.btn-mas');
    const btnMenos = qs(row, '.btn-menos');
    const btnEliminar = qs(row, '.btn-eliminar');

    if (btnMas) {
      btnMas.addEventListener('click', () => cambiarCantidad(row, +1));
    }
    if (btnMenos) {
      btnMenos.addEventListener('click', () => cambiarCantidad(row, -1));
    }
    if (btnEliminar) {
      btnEliminar.addEventListener('click', () => eliminarProducto(row));
    }
  });

  // Botón checkout: si está bloqueado, mostramos el aviso (ya visible);
  // si el usuario hace click estando bloqueado, solo resaltamos el aviso.
  const btnCheckout = document.getElementById('btn-checkout');
  const alerta = document.getElementById('alerta-checkout');
  if (btnCheckout && alerta) {
    btnCheckout.addEventListener('click', (e) => {
      if (btnCheckout.disabled) {
        // Si está deshabilitado, solo mostramos el aviso
        e.preventDefault();
        alerta.classList.remove('d-none');
        alerta.classList.add('shake');
        setTimeout(() => alerta.classList.remove('shake'), 600);
      } else {
        // Si está habilitado, iniciamos proceso con Mercado Pago
        fetch('/catalogo/carrito/crear_preferencia/', {
            method: "POST",
            headers: { "X-CSRFToken": CSRF_TOKEN }
        })
        .then(res => res.json())
        .then(data => {
            const mp = new MercadoPago(window.MP_PUBLIC_KEY, { locale: "es-PE" });
            mp.checkout({
                preference: { id: data.id },
                autoOpen: true
            });
        })
        .catch(err => {
            console.error("Error creando preferencia:", err);
        });
      }
    });
  }
});
