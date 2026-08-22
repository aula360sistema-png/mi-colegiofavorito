(function () {
    const grado = document.getElementById('filtro-grado');
    const seccion = document.getElementById('filtro-seccion');
    if (!grado || !seccion) return;

    function filtrarSecciones() {
        const g = grado.value;
        [...seccion.options].forEach(opt => {
            if (opt.value === '') return;
            opt.hidden = g !== '' && opt.dataset.grado !== g;
        });
        if (g !== '' && seccion.value !== '' && seccion.options[seccion.selectedIndex].hidden) {
            seccion.value = '';
        }
    }
    grado.addEventListener('change', filtrarSecciones);
    filtrarSecciones();

    const todos = document.getElementById('seleccionar-todos');
    const cajas = [...document.querySelectorAll('.checkbox-estudiante')];
    const contador = document.getElementById('contador-seleccionados');

    function actualizarContador() {
        const n = cajas.filter(c => c.checked).length;
        contador.textContent = n;
        if (todos) todos.checked = n > 0 && n === cajas.length;
    }
    if (todos) {
        todos.addEventListener('change', () => {
            cajas.forEach(c => { c.checked = todos.checked; });
            actualizarContador();
        });
    }
    cajas.forEach(c => c.addEventListener('change', actualizarContador));
    actualizarContador();
})();
