# Calculadora de impuesto específico al diésel

Sitio estático para GitHub Pages. Las facturas se guardan en el navegador del usuario; el archivo generado por la tarea contiene solamente los valores públicos del SII.

## Archivos

- `index.html`: calculadora mensual.
- `datos-sii.json`: datos oficiales que lee el botón **Actualizar valores SII**.
- `scripts/actualizar_datos_sii.py`: obtiene y ordena los valores publicados por el SII.
- `.github/workflows/actualizar-datos-sii.yml`: tarea mensual y opción de ejecución manual.

## Publicar en GitHub

1. Crea un repositorio y sube el contenido de esta carpeta a la raíz de la rama principal (`main`).
2. En **Settings → Pages**, configura la publicación desde la rama `main` y la carpeta `/ (root)`.
3. En **Settings → Actions → General → Workflow permissions**, permite que las acciones escriban en el repositorio. El flujo necesita guardar el archivo `datos-sii.json` actualizado.
4. Abre **Actions → Actualizar valores del SII → Run workflow** una vez para cargar los datos iniciales.
5. Abre la dirección de GitHub Pages y pulsa **Actualizar valores SII**. La calculadora buscará en `datos-sii.json` la UTM del mes y la tasa variable vigente en cada fecha de factura.

## Frecuencia

La tarea programada corre el día 2 de cada mes a las 13:17 UTC, después del cierre del mes anterior. Descarga la UTM y el historial semanal de tasas variables para el año actual y el anterior. También se puede iniciar manualmente desde la pestaña **Actions** si necesitas actualizar antes.

El botón de la página vuelve a cargar el último archivo publicado por la tarea; no consulta directamente al SII. Si se necesita una descarga inmediata desde el SII, ejecuta primero el flujo manual en **Actions** y luego pulsa el botón en la página.

## Datos y cálculo

- UTM mensual en pesos, según la fecha de cada factura.
- Tasa fija: `1,5 UTM/m³`.
- Tasa variable: valor del diésel cuya fecha de vigencia sea la más reciente que no supere la fecha de la factura.
- Importe por componente: `litros ÷ 1.000 × UTM en pesos × tasa en UTM/m³`.

Fuentes oficiales consultadas por el flujo:

- https://www.sii.cl/valores_y_fechas/utm/utm{year}.htm
- https://www.sii.cl/valores_y_fechas/mepco/mepco{year}.htm

La tabla del SII puede cambiar de formato. Si una descarga no se puede interpretar, el flujo falla visiblemente en **Actions** y conserva el último archivo válido.
