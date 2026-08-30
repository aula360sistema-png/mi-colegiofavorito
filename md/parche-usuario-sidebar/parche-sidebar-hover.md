# Parche: Sidebar Colapsado — Flyout de Submenú por Hover — Implementado

## Qué se hizo
Solo se tocó **CSS** (`static/css/dashboard.css`) — cero cambios de HTML y cero cambios de JS. Esto fue posible porque, al revisar la estructura real, cada `.menu-toggle` (botón) y su `.submenu` correspondiente ya son **hermanos directos** en el HTML — no hizo falta envolverlos en un contenedor nuevo (mi plan original suponía que sí haría falta; al verificar el HTML real, no era necesario).

## Los 3 problemas reales que encontré y corregí

1. **`.submenu { display: none }` sin excepción de hover** → se agregó una regla nueva que muestra el submenu al pasar el mouse sobre su botón, usando el selector de hermano adyacente (`.menu-toggle:hover + .submenu`) — sin JS.

2. **`.sidebar-nav` tenía `overflow-y: auto`**, que recorta cualquier elemento `position: absolute` que intente salir hacia la derecha, sin importar el CSS del flyout. Se cambió a `overflow-y: visible` **solo cuando el sidebar está colapsado** (en expandido, el scroll normal del menú se mantiene intacto).

3. **`.sidebar` no era `position: relative`**, así que el `left: 84px` del flyout no tenía una referencia fija de dónde empezar a medirse. Se agregó.

## Bonus: accesibilidad de teclado
Además del `:hover`, agregué `:focus-visible` (al tabular hasta el botón) y `:focus-within` (al tabular dentro del propio submenu) — así alguien que navegue sin mouse también puede abrir y usar el submenu colapsado, no solo quien usa mouse.

## Trade-off que debes revisar visualmente (no lo pude verificar yo, no tengo navegador para renderizar CSS)
Al quitar el `overflow-y: auto` del nav cuando está colapsado, si tu cuenta (ej. Director/Admin) tiene **muchos** módulos de primer nivel y la pantalla es de poca altura, los íconos colapsados podrían no entrar todos en la vista y no habría scroll para verlos. Esto es un trade-off consciente, no un descuido — pero como no tengo forma de renderizar y ver el resultado real en tu navegador, te pido que lo confirmes visualmente después de aplicar el parche, especialmente con el usuario que tenga más módulos visibles (probablemente `director` o `superadmin`).

## Archivo modificado
Solo `static/css/dashboard.css` (42 líneas nuevas, nada eliminado salvo el bloque que se reemplazó por la versión con el comentario explicativo).

## Verificación
No hay tests automatizados de CSS/JS en el proyecto (es normal, Django no los corre). Corrí la suite de `core` (que renderiza `home.html`, donde vive el sidebar) para confirmar que nada del lado de Python/templates se rompió:
```
python manage.py test core
Ran 45 tests — OK
```
La verificación visual real (que el hover se vea y comporte bien) queda pendiente de que la hagas tú en el navegador — es el único paso que no pude validar desde aquí.

## Cómo aplicarlo
1. Descomprime `parche-usuario-sidebar.zip` (mismo zip que el fix de usuario, ambos parches van juntos).
2. Copia `static/css/dashboard.css` sobre tu repo.
3. Si usas colector de estáticos (`collectstatic`) en producción, córrelo de nuevo para que Render sirva el CSS actualizado.
4. Prueba en escritorio, pantalla completa: colapsa el sidebar y pasa el mouse sobre un módulo con submenú (ej. "Estudiantes" en el menú de Administración).

## Si después de probarlo decides que igual quieres reemplazar el sidebar
Sigue siendo una opción válida a futuro — este parche resuelve el problema puntual sin tocar la base (temas de color por centro, responsive móvil, etc., que ya funcionan bien), pero si en algún momento el sidebar crece mucho más o quieres un patrón más robusto de UI, un reemplazo completo sigue sobre la mesa. Este parche no cierra esa puerta, solo resuelve lo urgente con el menor riesgo posible mientras tanto.
