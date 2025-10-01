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
        let html = `<div class='grid grid-cols-1 md:grid-cols-2 gap-4 mt-6'>`;
        html += `<div class='bg-white rounded-2xl shadow-lg p-6 flex flex-col gap-2'>`;
        html += `<div class='font-bold text-xl text-blue-800 mb-1 flex items-center gap-2'><svg xmlns='http://www.w3.org/2000/svg' class='h-6 w-6 text-blue-400' fill='none' viewBox='0 0 24 24' stroke='currentColor'><path stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M5.121 17.804A13.937 13.937 0 0112 15c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0z' /></svg> ${cliente.nombre || ''} ${cliente.apellido || ''}</div>`;
        html += `<div class='flex flex-col gap-1 text-gray-700'>`;
        html += `<div><b>Cédula:</b> ${cliente.nacionalidad || ''}${cliente.cedula || ''}</div>`;
        if (cliente.telefono) html += `<div><b>Teléfono:</b> ${cliente.telefono}</div>`;
        if (cliente.email) html += `<div><b>Email:</b> ${cliente.email}</div>`;
        if (cliente.direccion) html += `<div><b>Dirección:</b> ${cliente.direccion}</div>`;
        if (cliente.score !== undefined && cliente.score !== null) html += `<div><b>Score actual:</b> <span class='font-bold text-blue-600'>${cliente.score}</span></div>`;
        html += `</div>`;
        if (cliente.enriquecido) html += `<div class='mt-2 text-xs text-green-600 bg-green-50 rounded px-2 py-1'>Información enriquecida automáticamente desde la API externa.</div>`;
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
        // Historial de score si existe
        if (cliente.historial && cliente.historial.length > 0) {
            html += `<div class='bg-blue-50 rounded-2xl shadow p-6 flex flex-col gap-1'>`;
            html += `<div class='font-bold text-blue-700 mb-2'>Historial de Score</div>`;
            html += `<table class='min-w-full text-xs'><thead><tr><th class='px-2 py-1'>Fecha</th><th class='px-2 py-1'>Evento</th><th class='px-2 py-1'>Impacto</th><th class='px-2 py-1'>Comentario</th></tr></thead><tbody>`;
            cliente.historial.forEach(h => {
                html += `<tr><td class='px-2 py-1'>${h.fecha}</td><td class='px-2 py-1'>${h.evento}</td><td class='px-2 py-1'>${h.impacto}</td><td class='px-2 py-1'>${h.comentario || ''}</td></tr>`;
            });
            html += `</tbody></table>`;
            html += `</div>`;
        }
        html += `</div>`;
        return html;
    }

    function mostrarModalRegistro(cedula, nacionalidad) {
        if (!modal) return;
        document.getElementById('cedula-registro').value = cedula;
        document.getElementById('nacionalidad-registro').value = nacionalidad;
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
    
    const cancelarRegistroBtn = document.getElementById('cancelar-registro');
    if (cancelarRegistroBtn) {
        cancelarRegistroBtn.addEventListener('click', cerrarModal);
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

// --- ACCIONES DE REPORTES REALIZADOS ---
document.addEventListener('DOMContentLoaded', function() {
  // Botones de ver detalle
  document.querySelectorAll('.btn-ver-detalle').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const id = this.getAttribute('data-id');
      fetch(`/api/reporte_detalle/${id}`)
        .then(r => r.json())
        .then(data => {
          if (data.success && data.data) {
            renderDetalleReporteModal(data.data);
            document.getElementById('modal-detalle-reporte-overlay').classList.remove('hidden');
          } else {
            alert('No se pudo obtener el detalle del reporte.');
          }
        })
        .catch(() => alert('Error de conexión.'));
    });
  });
  // Botones de descargar
  document.querySelectorAll('.btn-descargar-reporte').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const id = this.getAttribute('data-id');
      window.open(`/api/descargar_reporte/${id}`, '_blank');
    });
  });
  // Botones de modificar reporte
  document.querySelectorAll('.btn-modificar-reporte').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const id = this.getAttribute('data-id');
      fetch(`/api/reporte_detalle/${id}`)
        .then(r => r.json())
        .then(data => {
          if (data.success && data.data) {
            renderEditarReporteModal(data.data, id);
            document.getElementById('modal-editar-reporte-overlay').classList.remove('hidden');
          } else {
            alert('No se pudo obtener el reporte para editar.');
          }
        })
        .catch(() => alert('Error de conexión.'));
    });
  });
  // Cerrar modal detalle
  const cerrarDetalle = document.getElementById('cerrar-modal-detalle-reporte');
  const overlayDetalle = document.getElementById('modal-detalle-reporte-overlay');
  if (cerrarDetalle && overlayDetalle) {
    cerrarDetalle.addEventListener('click', () => overlayDetalle.classList.add('hidden'));
    overlayDetalle.addEventListener('click', function(e) {
      if (e.target === overlayDetalle) overlayDetalle.classList.add('hidden');
    });
  }
  // Cerrar modal editar
  const cerrarEditar = document.getElementById('cerrar-modal-editar-reporte');
  const overlayEditar = document.getElementById('modal-editar-reporte-overlay');
  if (cerrarEditar && overlayEditar) {
    cerrarEditar.addEventListener('click', () => overlayEditar.classList.add('hidden'));
    overlayEditar.addEventListener('click', function(e) {
      if (e.target === overlayEditar) overlayEditar.classList.add('hidden');
    });
  }
  // Cancelar editar
  const cancelarEditar = document.getElementById('cancelar-editar-reporte');
  if (cancelarEditar && overlayEditar) {
    cancelarEditar.addEventListener('click', () => overlayEditar.classList.add('hidden'));
  }
  // Guardar cambios
  const formEditar = document.getElementById('form-editar-reporte');
  if (formEditar) {
    formEditar.addEventListener('submit', function(e) {
      e.preventDefault();
      const id = formEditar.getAttribute('data-id');
      const motivo = document.getElementById('input-motivo-reporte').value;
      const comentario = document.getElementById('input-comentario-estado') && !document.getElementById('campo-comentario-estado').classList.contains('hidden')
        ? document.getElementById('input-comentario-estado').value
        : document.getElementById('input-comentario-reporte').value;
      const monto = document.getElementById('input-monto-reporte') ? document.getElementById('input-monto-reporte').value : null;
      const estado = document.getElementById('input-estado-reporte').value;
      fetch(`/api/modificar_reporte/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motivo, comentario, monto, estado })
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          document.getElementById('mensaje-exito-editar-reporte').textContent = data.message;
          document.getElementById('mensaje-exito-editar-reporte').classList.remove('hidden');
          setTimeout(() => { window.location.reload(); }, 1200);
        } else {
          alert(data.error || 'No se pudo modificar el reporte.');
        }
      })
      .catch(() => alert('Error de conexión al guardar.'));
    });
  }
  // Inicializar tooltips vistosos
  if (window.tippy) {
    tippy('.tippy', {
      theme: 'light-border',
      animation: 'scale',
      arrow: true,
      placement: 'top',
      delay: [100, 50],
      maxWidth: 260
    });
  }
});

function renderDetalleReporteModal(data) {
  const c = data.cliente || {};
  const r = data.reporte || {};
  let html = `<div class='mb-4'>
    <div class='font-bold text-lg text-blue-700 mb-1'>${c.nombre || '-'} ${c.apellido || ''} <span class='text-xs text-gray-500'>(${c.nacionalidad || ''}${c.cedula || ''})</span></div>
    <div class='text-gray-700 text-sm mb-1'><b>Email:</b> ${c.email || '-'}</div>
    <div class='text-gray-700 text-sm mb-1'><b>Teléfono:</b> ${c.telefono || '-'}</div>
    <div class='text-gray-700 text-sm mb-1'><b>Dirección:</b> ${c.direccion || '-'}</div>
    <div class='text-gray-700 text-sm mb-1'><b>Score actual:</b> <span class='font-bold'>${c.score || '-'}</span></div>
    <div class='text-gray-700 text-sm mb-1'><b>Registrado:</b> ${c.registrado ? 'Sí' : 'No'}</div>
  </div>`;
  html += `<div class='border-t pt-4 mt-2'>
    <div class='font-bold text-base text-gray-900 mb-2'>Datos del Reporte</div>
    <div class='text-gray-700 text-sm mb-1'><b>Fecha:</b> ${r.fecha || '-'}</div>
    <div class='text-gray-700 text-sm mb-1'><b>Motivo:</b> ${r.motivo || '-'}</div>
    <div class='text-gray-700 text-sm mb-1'><b>Estado:</b> ${r.estado || '-'}</div>
    <div class='text-gray-700 text-sm mb-1'><b>Comentario:</b> ${r.comentario || '-'}</div>
    <div class='text-gray-700 text-sm mb-1'><b>Impacto:</b> ${r.impacto || '-'}</div>
    <div class='text-gray-700 text-sm mb-1'><b>Monto:</b> ${r.monto || '-'}</div>
  </div>`;
  // Historial de cambios
  if (data.historial && data.historial.length > 0) {
    html += `<div class='border-t pt-4 mt-4'>
      <div class='font-bold text-base text-blue-900 mb-2'>Historial de Cambios</div>
      <div class='overflow-x-auto'>
        <table class='min-w-full text-xs border rounded'>
          <thead class='bg-blue-50'>
            <tr>
              <th class='px-2 py-1'>Fecha</th>
              <th class='px-2 py-1'>Usuario</th>
              <th class='px-2 py-1'>Tipo</th>
              <th class='px-2 py-1'>De</th>
              <th class='px-2 py-1'>A</th>
              <th class='px-2 py-1'>Comentario</th>
            </tr>
          </thead>
          <tbody>`;
    data.historial.forEach(h => {
      html += `<tr>
        <td class='px-2 py-1 whitespace-nowrap'>${h.fecha}</td>
        <td class='px-2 py-1 whitespace-nowrap'>${h.usuario}</td>
        <td class='px-2 py-1 whitespace-nowrap'>${h.tipo_usuario}</td>
        <td class='px-2 py-1 whitespace-nowrap'>${h.estado_anterior}</td>
        <td class='px-2 py-1 whitespace-nowrap'>${h.estado_nuevo}</td>
        <td class='px-2 py-1 whitespace-nowrap'>${h.comentario || '-'}</td>
      </tr>`;
    });
    html += `</tbody></table></div></div>`;
  }
  document.getElementById('contenido-modal-detalle-reporte').innerHTML = html;
}

function renderEditarReporteModal(data, id) {
  const r = data.reporte || {};
  let html = `<div class='mb-4'>
    <label class='block text-sm font-semibold mb-1'>Motivo</label>
    <input type='text' id='input-motivo-reporte' class='w-full px-3 py-2 rounded border border-gray-300 mb-2' value='${r.motivo || ''}' required>
    <label class='block text-sm font-semibold mb-1'>Comentario</label>
    <textarea id='input-comentario-reporte' class='w-full px-3 py-2 rounded border border-gray-300 mb-2'>${r.comentario || ''}</textarea>
    <label class='block text-sm font-semibold mb-1'>Monto</label>
    <input type='number' id='input-monto-reporte' class='w-full px-3 py-2 rounded border border-gray-300 mb-2' value='${r.monto || ''}'>
    <label class='block text-sm font-semibold mb-1'>Estado</label>
    <select id='input-estado-reporte' class='w-full px-3 py-2 rounded border border-gray-300 mb-2'>
      <option value='pendiente' ${r.estado === 'pendiente' ? 'selected' : ''}>Pendiente</option>
      <option value='cerrado' ${r.estado === 'cerrado' ? 'selected' : ''}>Cerrado</option>
      <option value='aprobado' ${r.estado === 'aprobado' ? 'selected' : ''}>Aprobado</option>
      <option value='rechazado' ${r.estado === 'rechazado' ? 'selected' : ''}>Rechazado</option>
    </select>
  </div>`;
  document.getElementById('contenido-modal-editar-reporte').innerHTML = html;
  document.getElementById('form-editar-reporte').setAttribute('data-id', id);

  // Lógica para mostrar campo de comentario si cambia el estado
  const estadoOriginal = r.estado;
  const selectEstado = document.getElementById('input-estado-reporte');
  const campoComentario = document.getElementById('campo-comentario-estado');
  const inputComentarioEstado = document.getElementById('input-comentario-estado');
  const advertenciaEstado = document.getElementById('advertencia-estado');
  if (selectEstado && campoComentario && inputComentarioEstado && advertenciaEstado) {
    selectEstado.addEventListener('change', function() {
      if (this.value !== estadoOriginal) {
        campoComentario.classList.remove('hidden');
        inputComentarioEstado.required = true;
        if (this.value === 'pendiente') {
          advertenciaEstado.classList.remove('hidden');
        } else {
          advertenciaEstado.classList.add('hidden');
        }
      } else {
        campoComentario.classList.add('hidden');
        inputComentarioEstado.required = false;
        advertenciaEstado.classList.add('hidden');
      }
    });
    // Inicializar visibilidad
    selectEstado.dispatchEvent(new Event('change'));
  }
}
