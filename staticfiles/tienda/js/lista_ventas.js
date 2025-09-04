$(document).ready(function () {
    $('#ventas-table').DataTable({
        responsive: true,
        pageLength: 10,
        lengthMenu: [10, 25, 50, 100],
        order: []
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    document.querySelectorAll('.confirmarEntrega').forEach(btn => {
        btn.addEventListener("click", function() {
            const id = this.dataset.ventaId;
            
            Swal.fire({
                title: '¿Confirmar entrega de artículo(s)?',
                text: '¿Desea confirmar la entrega?',
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: 'Sí, confirmar',
                cancelButtonText: 'Cancelar',
                reverseButtons: true,
                allowOutsideClick: false,
                customClass: {
                    popup: 'mi-popup-sw',
                    container: 'mi-container-sw'
                }
            }).then((result) => {
                if (result.isConfirmed) {
                    Swal.fire({
                        title: 'Procesando...',
                        text: 'Por favor espere',
                        allowOutsideClick: false,
                        allowEscapeKey: false,
                        customClass: {
                            popup: 'mi-popup-sw',
                            container: 'mi-container-sw'
                        },
                        didOpen: () => {
                            Swal.showLoading();
                        }
                    });

                    fetch(`/lista_ventas/confirmar_entrega/${id}/`, {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": csrfToken,
                            "Content-Type": "application/json"
                        }
                    })
                    .then(response => {
                        if (!response.ok) throw new Error("Error en la respuesta");
                        return response.json();
                    })
                    .then(data => {
                        // Ocultar el loading
                        Swal.close();
                        Swal.fire({
                            title: 'Éxito',
                            text: data.message,
                            icon: 'success',
                            confirmButtonText: 'OK',
                            customClass: {
                                popup: 'mi-popup-sw',
                                container: 'mi-container-sw'
                            }
                        }).then(() => {
                            window.location.reload();
                        });
                    })
                    .catch(error => {
                        // Ocultar el loading
                        Swal.close();
                        Swal.fire({
                            title: 'Error',
                            text: 'Ocurrió un problema al confirmar entrega.',
                            icon: 'error',
                            confirmButtonText: 'Cerrar',
                            customClass: {
                                popup: 'mi-popup-sw',
                                container: 'mi-container-sw'
                            }
                        });
                    });
                }
            });
        });
    });
});