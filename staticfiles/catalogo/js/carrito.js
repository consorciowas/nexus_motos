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

// Validadores
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const onlyDigits = /^\d+$/;

function validateFacturaFields(data) {
  // RUC 11 dígitos, email válido
  if (!onlyDigits.test(data.ruc || '') || String(data.ruc || '').length !== 11) return false;
  if (!emailRegex.test(data.correo || '')) return false;
  if (!data.razon_social || !data.direccion || !data.telefono) return false;
  return true;
}

function setReadonly(formEl, readonly) {
  const cls = 'input-readonly';
  formEl.querySelectorAll('input,select').forEach(el => {
    // No aplicar a los campos de la sección factura
    if (el.closest('#factura-nl-fields')) return;

    if (readonly) {
      el.classList.add(cls);
      el.setAttribute('readonly', 'readonly');
      //el.setAttribute('disabled', 'disabled');
    } else {
      el.classList.remove(cls);
      el.removeAttribute('readonly');
      //el.removeAttribute('disabled');
    }
  });
}

// ==== LOGUEADO: checkbox -> modal factura (opcional) ====
const checkFactura = document.getElementById('check-factura');
if (checkFactura) {
  const modalFacturaEl = document.getElementById('modalFactura');
  const modalFactura = new bootstrap.Modal(modalFacturaEl);
  const formFactura = document.getElementById('form-factura');
  const btnCancelFactura = document.getElementById('cancel-factura');
  const btnSaveFactura = document.getElementById('save-factura');

  checkFactura.addEventListener('change', () => {
    if (checkFactura.checked) {
      // Si marca, abrimos modal
      modalFactura.show();
    } else {
      // Si desmarca y había factura guardada → confirmar
      if (window.FACTURA_GUARDADA) {
        e.preventDefault(); // prevenimos cambio inmediato
        Swal.fire({
          title: '¿Seguro que ya no deseas factura?',
          text: 'Se eliminarán los datos de facturación guardados.',
          icon: 'warning',
          showCancelButton: true,
          confirmButtonText: 'Sí, eliminar',
          cancelButtonText: 'No, mantener',
          allowOutsideClick: false,
          allowEscapeKey: false
        }).then(result => {
          if (result.isConfirmed) {
            checkFactura.checked = false;
            formFactura.reset();
            window.FACTURA_GUARDADA = false;
            fetch('/catalogo/carrito/factura/clear/', { 
              method: 'POST', 
              headers: { 'X-CSRFToken': CSRF_TOKEN } 
            });
          } else {
            checkFactura.checked = true;
          }
        });
      }
    }
  });

  btnCancelFactura.addEventListener('click', () => {
    checkFactura.checked = false;
    formFactura.reset();
    fetch('/catalogo/carrito/factura/clear/', { method: 'POST', headers: { 'X-CSRFToken': CSRF_TOKEN } });
    window.FACTURA_GUARDADA = false;
  });

  btnSaveFactura.addEventListener('click', async () => {
    const data = Object.fromEntries(new FormData(formFactura).entries());
    // validar
    if (!validateFacturaFields(data)) {
      alert('Por favor completa correctamente RUC (11 dígitos), correo y todos los campos.');
      return;
    }
    mostrarSpinner();
    try {
      const res = await fetch('/catalogo/carrito/factura/set/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
        body: JSON.stringify(data)
      });
      const js = await res.json();
      if (!js.success) throw new Error(js.message || 'No se pudo guardar la factura');
      window.FACTURA_GUARDADA = true;
      modalFactura.hide();
    } catch (e) {
      console.error(e);
      Swal.fire({
          title: 'Error',
          text: 'No se pudo guardar los datos de facturación',
          icon: 'error',
          allowOutsideClick: false,
          allowEscapeKey: false
      });
      checkFactura.checked = false;
    } finally {
      ocultarSpinner();
    }
  });
}

// ==== NO LOGUEADO: modal cliente + factura opcional ====
const modalClienteEl = document.getElementById('modalCliente');
const modalCliente = modalClienteEl ? new bootstrap.Modal(modalClienteEl) : null;
const formCliente = document.getElementById('form-cliente');
const btnSaveCliente = document.getElementById('save-cliente');
const btnCancelCliente = document.getElementById('cancel-cliente');
const tipoDocEl = document.getElementById('tipo_doc');
const numDocEl = document.getElementById('num_doc');
const checkFacturaNL = document.getElementById('check-factura-nl');
const facturaNLSec = document.getElementById('factura-nl-fields');

if (checkFacturaNL && facturaNLSec) {
  checkFacturaNL.addEventListener('change', () => {
    if (checkFacturaNL.checked) {
      facturaNLSec.style.display = 'block';
    } else {
      facturaNLSec.style.display = 'none';
      // limpiar campos de factura al desmarcar
      facturaNLSec.querySelectorAll('input').forEach(i => i.value = '');
    }
    evaluateClienteForm();
  });
}

  function validateDoc(tipo, nro) {
    if (!onlyDigits.test(nro || '')) return false;
    if (tipo === 'DNI') return String(nro).length === 8;
    if (tipo === 'CE') return String(nro).length === 12;
    return false;
  }

  function evaluateClienteForm() {
    console.log("entraaaaa")
    if (!formCliente) return;
    const fd = Object.fromEntries(new FormData(formCliente).entries());
    console.log(fd)
    // Documento
    let ok = validateDoc(fd.tipo_documento, fd.documento);
    console.log("okkkk")
    console.log(ok)
    // Datos base
    ok = ok && fd.nombre && fd.paterno && fd.materno && emailRegex.test(fd.correo || '');
    console.log(ok)
    console.log(ok && fd.telefono)
    console.log(ok && fd.telefono && fd.direccion)
    console.log(ok && fd.telefono && fd.direccion && fd.nacimiento)
    console.log(ok && fd.telefono && fd.direccion && fd.nacimiento && fd.sexo)
    ok = ok && fd.telefono && fd.direccion && fd.nacimiento && fd.sexo;
    console.log(ok && fd.telefono)
    // Si factura NL activo, validar
    if (checkFacturaNL && checkFacturaNL.checked) {
      const f = {
        ruc: fd.ruc,
        razon_social: fd.razon_social,
        telefono: fd.telefono_factura,
        correo: fd.correo_factura,
        direccion: fd.direccion_factura
      };
      ok = ok && validateFacturaFields(f);
    }
    if (btnSaveCliente) btnSaveCliente.disabled = !ok;
  }

  if (formCliente) {
    formCliente.addEventListener('input', evaluateClienteForm);
  }

  // Buscar cliente por documento al salir del campo
  if (numDocEl) {
    // Permitir solo números al escribir
    numDocEl.addEventListener('input', () => {
      numDocEl.value = numDocEl.value.replace(/\D/g, ''); // elimina cualquier letra o símbolo
    });

    numDocEl.addEventListener('blur', async () => {
      const tipo = tipoDocEl.value;
      const doc = numDocEl.value.trim();

      // resetear estilo
      numDocEl.classList.remove('is-invalid');

      // si no cumple -> marcar error
      if (doc && !validateDoc(tipo, doc)) {
        numDocEl.classList.add('is-invalid');
        return; // no seguir si no es válido
      }

      if (!validateDoc(tipo, doc)) return; // si está vacío o inválido, salir
      mostrarSpinner();
      try {
        const url = `/catalogo/carrito/cliente/buscar/?tipo=${encodeURIComponent(tipo)}&doc=${encodeURIComponent(doc)}`;
        const res = await fetch(url, { headers: { 'X-CSRFToken': CSRF_TOKEN }});
        const js = await res.json();
        if (js.exists) {
          // autocompletar y bloquear
          const map = js.data || {};
          const set = (name, val) => {
            const el = formCliente.querySelector(`[name="${name}"]`);
            if (el) el.value = val || '';
          };
          set('nombre', map.cliente_nombre);
          set('paterno', map.cliente_paterno);
          set('materno', map.cliente_materno);
          set('correo', map.cliente_email);
          set('telefono', map.cliente_telefono);
          set('direccion', map.cliente_direccion);
          set('nacimiento', map.cliente_fechanac);
          set('sexo', map.cliente_sexo);

          // bloquear edición
          setReadonly(formCliente, true);
          // permitir editar solo “documento”, “tipo_documento” y checkbox factura
          ['tipo_documento','documento'].forEach(name => {
            const el = formCliente.querySelector(`[name="${name}"]`);
            if (el) { el.classList.remove('input-readonly'); el.removeAttribute('readonly'); el.removeAttribute('disabled'); }
          });
          if (checkFacturaNL) { checkFacturaNL.classList.remove('input-readonly'); checkFacturaNL.removeAttribute('readonly'); checkFacturaNL.removeAttribute('disabled'); }
        } else {
          // desbloquear para nuevo registro
          setReadonly(formCliente, false);
        }
      } catch (e) {
        console.error(e);
      } finally {
        ocultarSpinner();
        evaluateClienteForm();
      }
    });
  }

  if (btnCancelCliente && modalCliente) {
    btnCancelCliente.addEventListener('click', () => {
      // limpiar y desbloquear todo
      formCliente.reset();
      setReadonly(formCliente, false);
      if (checkFacturaNL) { checkFacturaNL.checked = false; facturaNLSec.style.display = 'none'; }
    });
  }

  if (btnSaveCliente) {
    btnSaveCliente.addEventListener('click', async () => {
      const fd = Object.fromEntries(new FormData(formCliente).entries());
      // Si el cliente existía (campos bloqueados) NO creamos; si no, creamos
      const existed = formCliente.querySelector('input[name="nombre"]').hasAttribute('readonly');

      mostrarSpinner();
      try {
        if (!existed) {
          // Registrar cliente
          const res = await fetch('/catalogo/carrito/cliente/registrar/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body: JSON.stringify(fd)
          });
          const js = await res.json();
          if (!js.success) throw new Error(js.message || 'No se pudo registrar el cliente');
        }
        // Si pidió factura dentro del modal NL, guardamos en sesión
        if (checkFacturaNL && checkFacturaNL.checked) {
          const factura = {
            ruc: fd.ruc,
            razon_social: fd.razon_social,
            telefono: fd.telefono_factura,
            correo: fd.correo_factura,
            direccion: fd.direccion_factura
          };
          if (!validateFacturaFields(factura)) throw new Error('Datos de factura inválidos');
          const fRes = await fetch('/catalogo/carrito/factura/set/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body: JSON.stringify(factura)
          });
          const fj = await fRes.json();
          if (!fj.success) throw new Error(fj.message || 'No se pudo guardar la factura');
        } else {
          await fetch('/catalogo/carrito/factura/clear/', { method: 'POST', headers: { 'X-CSRFToken': CSRF_TOKEN } });
        }

        // cerrar modal y lanzar Mercado Pago (reutiliza handler actual)
        modalCliente.hide();

        // Disparar exactamente tu flujo actual de MP:
        await iniciarCheckoutMP();
      } catch (e) {
        console.error(e);
        alert(e.message || 'Ocurrió un error');
      } finally {
        ocultarSpinner();
      }
    });
  }

async function iniciarCheckoutMP() {
  try {
    mostrarSpinner();

    const res = await fetch('/catalogo/carrito/crear_preferencia/', {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF_TOKEN }
    });
    const data = await res.json();

    const mp = new MercadoPago(window.MP_PUBLIC_KEY, { locale: 'es-PE' });
    mp.checkout({
      preference: { id: data.id },
      autoOpen: true
    });
  } catch (e) {
    console.error('Error creando preferencia:', e);
    alert('No se pudo iniciar el pago.');
  } finally {
    ocultarSpinner();
  }
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

  if (btnCheckout) {
    btnCheckout.addEventListener('click', async (e) => {
      // 1. Si está deshabilitado → mostrar aviso
      if (btnCheckout.disabled) {
        e.preventDefault();
        if (alerta) {
          alerta.classList.remove('d-none');
          alerta.classList.add('shake');
          setTimeout(() => alerta.classList.remove('shake'), 600);
        }
        return;
      }

      // 2. Si no autenticado → abrir modal cliente
      if (!window.IS_AUTH && modalCliente) {
        e.preventDefault();
        modalCliente.show();
        return;
      }

      // 3. Si autenticado y quiere factura → abrir modal factura primero
      if (window.IS_AUTH && checkFactura && checkFactura.checked) {
        const mustConfirm = !window.FACTURA_GUARDADA;
        if (mustConfirm) {
          e.preventDefault();
          const mf = bootstrap.Modal.getOrCreateInstance(document.getElementById('modalFactura'));
          mf.show();
          return;
        }
      }

      // 4. Si todo OK → iniciar checkout con MP
      await iniciarCheckoutMP();
    });
  }

});
