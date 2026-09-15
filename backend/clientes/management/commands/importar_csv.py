import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand

from clientes.models import Cliente, Ingreso, Servicio
from empleados.models import Empleado

EJEMPLOS_DIR = Path(__file__).resolve().parents[4] / 'docs' / 'importacion_ejemplo'


class Command(BaseCommand):
    """
    Ejemplo minimo de importacion desde un archivo externo (CSV en vez de la
    planilla de Google Sheets del original), pensado para mostrar el mismo
    contraste que documentaba el proyecto original:

    - `importar_clientes()` es IDEMPOTENTE: usa get_or_create por
      nombre_contacto, asi que correr el comando dos veces con el mismo CSV
      no duplica nada.
    - `importar_ingresos_historicos()` es a proposito NO IDEMPOTENTE: usa
      .create() sin comprobar si esa fila ya se importo antes. Es la misma
      trampa real que tenia `importar_ingresos` en el proyecto original:
      correr el import dos veces duplica los ingresos historicos. Se deja
      asi a proposito, documentado, como ejemplo de la diferencia -- en un
      caso real conviene agregar una clave de deduplicacion (por ejemplo,
      un numero de folio externo) antes de cargar datos de produccion.

    Uso: python manage.py importar_csv [--solo clientes|catalogo|ingresos]
    Por defecto usa los CSV de ejemplo en docs/importacion_ejemplo/.

    El catalogo (Servicio/Empleado) no viene de un CSV -- son los mismos
    nombres/codigos fijados en docs/DATOS_FICTICIOS.md, sembrados de forma
    idempotente para que los ingresos de ejemplo tengan a quien engancharse
    en una base recien migrada.
    """

    help = 'Importa clientes y catalogo (idempotente) + ingresos historicos (no idempotente) desde CSV.'

    SERVICIOS = [
        dict(codigo='LIMP-STD', nombre='Limpieza estándar', categoria='estandar',
             tarifa_cliente=Decimal('15'), compensacion_tipo='por_hora', compensacion_valor=Decimal('10')),
        dict(codigo='LIMP-NOC', nombre='Limpieza industrial nocturna', categoria='premium',
             tarifa_cliente=Decimal('20'), compensacion_tipo='porcentaje_base', compensacion_valor=Decimal('100'),
             cruza_medianoche=True),
        dict(codigo='MANT-TEC', nombre='Mantenimiento técnico', categoria='estandar',
             tarifa_cliente=Decimal('18'), compensacion_tipo='por_hora', compensacion_valor=Decimal('12')),
    ]
    EMPLEADOS = [
        dict(nombre='TEST-Diego', categoria='estandar'),
        dict(nombre='TEST-Sofia', categoria='estandar'),
        dict(nombre='TEST-Marta', categoria='estandar'),
        dict(nombre='TEST-Julia', categoria='premium'),
    ]

    def add_arguments(self, parser):
        parser.add_argument('--solo', choices=['clientes', 'catalogo', 'ingresos'], default=None)
        parser.add_argument('--clientes-csv', default=str(EJEMPLOS_DIR / 'clientes.csv'))
        parser.add_argument('--ingresos-csv', default=str(EJEMPLOS_DIR / 'ingresos_historicos.csv'))

    def handle(self, *args, **options):
        if options['solo'] in (None, 'clientes'):
            self.importar_clientes(options['clientes_csv'])
        if options['solo'] in (None, 'catalogo'):
            self.importar_catalogo()
        if options['solo'] in (None, 'ingresos'):
            self.importar_ingresos_historicos(options['ingresos_csv'])

    def importar_catalogo(self):
        """Idempotente: get_or_create por codigo/nombre. Ver docs/DATOS_FICTICIOS.md."""
        creados = 0
        for original in self.SERVICIOS:
            datos = dict(original)  # copia: no mutar la constante de clase entre corridas
            _, creado = Servicio.objects.get_or_create(codigo=datos.pop('codigo'), defaults=datos)
            creados += int(creado)
        for original in self.EMPLEADOS:
            datos = dict(original)
            _, creado = Empleado.objects.get_or_create(nombre=datos.pop('nombre'), defaults=datos)
            creados += int(creado)
        self.stdout.write(f'Catálogo (servicios + empleados): {creados} creados de {len(self.SERVICIOS) + len(self.EMPLEADOS)} (idempotente).')

    def importar_clientes(self, ruta):
        """Idempotente: get_or_create por nombre_contacto."""
        creados = 0
        existentes = 0
        with open(ruta, encoding='utf-8') as f:
            for fila in csv.DictReader(f):
                _, creado = Cliente.objects.get_or_create(
                    nombre_contacto=fila['nombre_contacto'],
                    defaults={
                        'nif': fila.get('nif', ''),
                        'telefono': fila.get('telefono', ''),
                        'email': fila.get('email', ''),
                        'iva_porcentaje': self._decimal(fila.get('iva_porcentaje'), Decimal('21.0')),
                    },
                )
                creados += int(creado)
                existentes += int(not creado)
        self.stdout.write(f'Clientes: {creados} creados, {existentes} ya existian (idempotente).')

    def importar_ingresos_historicos(self, ruta):
        """
        NO idempotente a proposito (ver docstring de la clase). Busca
        Cliente/Empleado/Servicio por nombre/codigo -- si alguno no existe
        todavia, omite la fila con un aviso en vez de crear datos a medias.
        """
        creados = 0
        omitidos = 0
        with open(ruta, encoding='utf-8') as f:
            for fila in csv.DictReader(f):
                cliente = Cliente.objects.filter(nombre_contacto=fila['cliente_nombre']).first()
                empleado = Empleado.objects.filter(nombre=fila['empleado_nombre']).first()
                servicio = Servicio.objects.filter(codigo=fila['servicio_codigo']).first()
                if not (cliente and empleado and servicio):
                    self.stdout.write(self.style.WARNING(
                        f"! Fila omitida (falta cliente/empleado/servicio): {fila}"
                    ))
                    omitidos += 1
                    continue

                Ingreso.objects.create(
                    cliente=cliente,
                    empleado=empleado,
                    servicio=servicio,
                    fecha=datetime.strptime(fila['fecha'], '%Y-%m-%d').date(),
                    horas=self._decimal(fila.get('horas'), Decimal('0')),
                )
                creados += 1
        self.stdout.write(f'Ingresos históricos: {creados} creados, {omitidos} omitidos.')
        self.stdout.write(self.style.WARNING(
            'Aviso: este paso NO es idempotente -- volver a correrlo con el mismo CSV '
            'duplica estos ingresos. Es intencional, ver el docstring del comando.'
        ))

    @staticmethod
    def _decimal(valor, default):
        if not valor:
            return default
        try:
            return Decimal(str(valor).replace(',', '.'))
        except InvalidOperation:
            return default
