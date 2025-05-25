// Sicred - Consulta y registro de cliente vía AJAX con modal

document.addEventListener('DOMContentLoaded', function() {
    const formConsulta = document.getElementById('form-consulta-cliente');
    const nacionalidadInput = document.getElementById('nacionalidad');
    const cedulaInput = document.getElementById('identificador');
    const resultadoDiv = document.getElementById('resultado-consulta');
    const modal = document.getElementById('modal-registro');
    const modalOverlay = document.getElementById('modal-overlay');
    const cerrarModalBtn = document.getElementById('cerrar-modal');
    const formRegistro = document.getElementById('form-registro-persona');
    const mensajeExito = document.getElementById('mensaje-exito');
    let timeoutModal = null;

    if (formConsulta) {
        formConsulta.addEventListener('submit', function(e) {
            e.preventDefault();
            const cedula = cedulaInput.value.trim();
            const nacionalidad = nacionalidadInput.value;
            if (!cedula) return;
            resultadoDiv.innerHTML = '<div class="text-gray-500 py-4">Consultando...</div>';
            fetch('/api/consulta_cedula', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cedula, nacionalidad })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success && data.cliente) {
                    resultadoDiv.innerHTML = renderTarjetasCliente(data.cliente);
                } else if (data.registro) {
                    mostrarModalRegistro(data.cedula, data.nacionalidad);
                } else if (data.error) {
                    resultadoDiv.innerHTML = `<div class='bg-red-100 border border-red-200 rounded p-4 text-red-800'>${data.error}</div>`;
                }
            })
            .catch(() => {
                resultadoDiv.innerHTML = '<div class="bg-red-100 border border-red-200 rounded p-4 text-red-800">Error de conexión con el servidor.</div>';
            });
        });
    }

    function renderTarjetasCliente(cliente) {
        // Tarjeta principal con datos organizados y modernos
        let html = `<div class='grid grid-cols-1 md:grid-cols-2 gap-4 mt-6'>`;
        html += `<div class='bg-white rounded-2xl shadow-lg p-6 flex flex-col gap-2'>`;
        html += `<div class='font-bold text-xl text-blue-800 mb-1 flex items-center gap-2'><svg xmlns='http://www.w3.org/2000/svg' class='h-6 w-6 text-blue-400' fill='none' viewBox='0 0 24 24' stroke='currentColor'><path stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M5.121 17.804A13.937 13.937 0 0112 15c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0z' /></svg>${cliente.primer_nombre || ''} ${cliente.segundo_nombre || ''} ${cliente.primer_apellido || ''} ${cliente.segundo_apellido || ''}</div>`;
        html += `<div class='flex flex-col gap-1 text-gray-700'>`;
        html += `<div><b>Cédula:</b> ${cliente.nacionalidad || ''}${cliente.cedula || ''}</div>`;
        if (cliente.rif) html += `<div><b>RIF:</b> ${cliente.rif}</div>`;
        if (cliente.fecha_nac) html += `<div><b>Fecha de nacimiento:</b> ${cliente.fecha_nac}</div>`;
        html += `</div>`;
        // Botones de acción SIEMPRE que haya cédula
        if (cliente.cedula && cliente.nacionalidad) {
            html += `<div class='mt-4 flex gap-4'>`;
            if (cliente.id) {
                html += `<a href='/empresa/reportar_cliente/${cliente.id}' class='px-4 py-2 rounded-lg font-bold text-white bg-red-500 hover:bg-red-700 shadow'>Reportar cliente</a>`;
                html += `<a href='/empresa/modificar_score/${cliente.id}' class='px-4 py-2 rounded-lg font-bold text-white bg-blue-500 hover:bg-blue-700 shadow'>Modificar score</a>`;
            } else {
                html += `<a href='/empresa/reportar_cliente?cedula=${cliente.cedula}&nacionalidad=${cliente.nacionalidad}' class='px-4 py-2 rounded-lg font-bold text-white bg-red-500 hover:bg-red-700 shadow'>Reportar cliente</a>`;
                html += `<a href='/empresa/modificar_score?cedula=${cliente.cedula}&nacionalidad=${cliente.nacionalidad}' class='px-4 py-2 rounded-lg font-bold text-white bg-blue-500 hover:bg-blue-700 shadow'>Modificar score</a>`;
            }
            html += `</div>`;
        }
        html += `</div>`;
        // Tarjeta de datos de votación si existen
        if (cliente.cne) {
            html += `<div class='bg-blue-50 rounded-2xl shadow p-6 flex flex-col gap-1'>`;
            html += `<div class='font-bold text-blue-700 mb-2'>Datos de Votación</div>`;
            if (cliente.cne.estado) html += `<div><b>Estado:</b> ${cliente.cne.estado}</div>`;
            if (cliente.cne.municipio) html += `<div><b>Municipio:</b> ${cliente.cne.municipio}</div>`;
            if (cliente.cne.parroquia) html += `<div><b>Parroquia:</b> ${cliente.cne.parroquia}</div>`;
            if (cliente.cne.centro_electoral) html += `<div><b>Centro Electoral:</b> ${cliente.cne.centro_electoral}</div>`;
            html += `</div>`;
        }
        html += `</div>`;
        return html;
    }

    function mostrarModalRegistro(cedula, nacionalidad) {
        if (!modal) return;
        document.getElementById('modal-cedula').value = cedula;
        document.getElementById('modal-nacionalidad').value = nacionalidad;
        modal.classList.remove('hidden');
        modalOverlay.classList.remove('hidden');
        mensajeExito.classList.add('hidden');
        formRegistro.classList.remove('hidden');
    }

    if (cerrarModalBtn) {
        cerrarModalBtn.addEventListener('click', cerrarModal);
    }
    if (modalOverlay) {
        modalOverlay.addEventListener('click', cerrarModal);
    }

    function cerrarModal() {
        modal.classList.add('hidden');
        modalOverlay.classList.add('hidden');
        if (timeoutModal) clearTimeout(timeoutModal);
    }

    if (formRegistro) {
        formRegistro.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(formRegistro);
            fetch('/api/registrar_persona', {
                method: 'POST',
                body: formData
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    formRegistro.classList.add('hidden');
                    mensajeExito.classList.remove('hidden');
                    timeoutModal = setTimeout(cerrarModal, 5000);
                } else if (data.error) {
                    alert(data.error);
                }
            })
            .catch(() => alert('Error de conexión al registrar.'));
        });
    }
});
