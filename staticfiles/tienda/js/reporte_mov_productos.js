const getCookie = (name) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const spinner = document.getElementById('spinner');
const btnBuscar = document.getElementById('btnBuscar');

btnBuscar.addEventListener('click', function(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('fecha_inicio', document.getElementById('fecha_inicio').value);
    fd.append('fecha_fin', document.getElementById('fecha_fin').value);
    fd.append('producto_id', document.getElementById('producto_id').value);

    const url = this.dataset.url;

    spinner.classList.remove("d-none");
    btnBuscar.disabled = true;

    fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: fd
    })
    .then(res => res.json())
    .then(json => {
        let html = '';
        json.data.forEach(item => {
            html += `<h5 class="bg-primary text-white p-2 mt-4">${item.producto}</h5>`;
            html += `<table class="table table-bordered table-sm tabla-mov">
                        <thead class="thead-dark">
                          <tr>
                            <th>MODELO</th><th>MARCA</th><th>FECHA MOV.</th><th>TIPO MOV.</th>
                            <th>TIPO DOC.</th><th>NUM. DOC.</th><th>CANT. ENTRADA</th><th>PRECIO ENTRADA</th>
                            <th>CANT. SALIDA</th><th>PRECIO SALIDA</th><th>SALDO</th>
                          </tr>
                        </thead><tbody>`;
            item.movimientos.forEach(m => {
                html += `<tr>
                    <td>${m.producto_modelo}</td><td>${m.producto_marca}</td><td>${m.fecha_mov}</td>
                    <td>${m.tipo_mov}</td><td>${m.tipo_doc}</td><td>${m.num_doc}</td>
                    <td>${m.cant_entrada || ''}</td><td>${m.precio_entrada || ''}</td>
                    <td>${m.cant_salida || ''}</td><td>${m.precio_salida || ''}</td>
                    <td>${m.saldo}</td>
                </tr>`;
            });
            html += `</tbody></table>`;
        });

        document.getElementById('tabla_resultado').innerHTML = html;

        document.querySelectorAll('.tabla-mov').forEach(table => {
            $(table).DataTable({
                dom: 'Bfrtip',
                buttons: ['excel', 'csv', 'pdf', 'print'],
                paging: false,
                searching: true,
                ordering: false
            });
        });
    })
    .catch(error => {
        console.error("Error al buscar mov. productos:", error);
    })
    .finally(() => {
        spinner.classList.add("d-none");
        btnBuscar.disabled = false;
    });
});