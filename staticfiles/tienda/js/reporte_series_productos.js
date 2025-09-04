$(document).ready(function () {
    let lastProducto = null;

    let tabla = $('#tablaSeries').DataTable({
        dom: 'Bfrtip',
        buttons: ['excelHtml5', 'csvHtml5', 'pdfHtml5'],
        responsive: true,
        language: { url: '//cdn.datatables.net/plug-ins/1.10.25/i18n/Spanish.json' },
        data: [],
        columns: [
            { data: 'serie' },
            {
                data: 'situacion',
                render: function (data) {
                    return data == 1
                        ? '<span style="color:green;font-weight:bold;">DISPONIBLE</span>'
                        : '<span style="color:red;font-weight:bold;">EXTRAÍDO</span>';
                }
            },
            { data: 'fecha_entrada' },
            { data: 'num_doc_entrada' },
            { data: 'tipo_doc_entrada' },
            { data: 'fecha_salida' },
            { data: 'num_doc_salida' },
            { data: 'tipo_doc_salida' }
        ],
        order: [], // Desactivar orden inicial
        searching: false, // Quitar el buscador
        ordering: false,  // Quitar el ordenamiento por columnas
        rowCallback: function (row, data, index) {
            if (data.separador) {
                // Reemplaza completamente la fila con el separador
                $(row).html(`<td colspan="8" style="background-color:#f2f2f2;font-weight:bold">${data.producto}</td>`);
            }
        },
        rowId: function (a) {
            return a.separador ? 'separador_' + Math.random() : a.serie;
        },
        createdRow: function (row, data, dataIndex) {
            if (data.separador) {
                // Evita que DataTables intente acceder a columnas inexistentes
                $(row).addClass('separador');
            }
        }
    });

    $('#btnBuscar').on('click', function () {
        const fecha_inicio = $('#fecha_inicio').val();
        const fecha_fin = $('#fecha_fin').val();
        const producto_id = $('#producto_id').val();

        $('#spinner').removeClass("d-none");
        $('#btnBuscar').prop("disabled", true);

        $.ajax({
            url: '/buscar_series_productos/',
            type: 'POST',
            headers: { "X-CSRFToken": $('input[name="csrfmiddlewaretoken"]').val() },
            data: { fecha_inicio, fecha_fin, producto_id },
            success: function (res) {
                lastProducto = null; // reset para que rowCallback funcione correctamente
                tabla.clear().rows.add(res.datos).draw();
            },
            error: function (err) {
                alert('Ocurrió un error al buscar.');
                console.log(err);
            }
        })
        .always(function () {
            $('#spinner').addClass("d-none");
            $('#btnBuscar').prop("disabled", false);
        });
    });
});
