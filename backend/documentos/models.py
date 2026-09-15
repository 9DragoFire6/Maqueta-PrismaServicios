from django.db import models


class PlantillaClausulasContrato(models.Model):
    """
    Texto en Markdown de las clausulas 2 en adelante del contrato (la
    Seccion 1 -- Service Details -- sigue siendo 100% automatica, armada
    desde los AcuerdoServicio de cada contrato, ver
    documentos/utils.py:generar_pdf_contrato).

    Fila unica (singleton, ver obtener_plantilla_activa() en
    documentos/utils.py): siempre se lee/edita la misma instancia. El
    historial de versiones anteriores no se duplica aca -- queda completo
    en auditlog.LogEntry (registrada mas abajo), que ademas registra quien
    y cuando.

    Formato Markdown soportado (deliberadamente minimo, ver
    documentos/utils.py:_clausulas_flowables): '## ' para el titulo de una
    seccion, lineas sueltas como parrafo, lineas que empiezan con '- ' como
    lista con vinetas, y '**texto**' para negrita. No hay numeracion
    automatica de clausulas: renumerar es responsabilidad de quien edita,
    igual que editar un contrato en un procesador de texto.
    """
    contenido = models.TextField()
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Plantilla de clausulas (actualizada {self.actualizado_en:%d/%m/%Y})"


# Modulo de Auditoria: registrada junto con Contrato/AcuerdoServicio para que
# cada cambio a las clausulas del contrato quede en el historial -- quien la
# edito y que cambio exactamente.
from auditlog.registry import auditlog

auditlog.register(PlantillaClausulasContrato)
