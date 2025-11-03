"""Plugin class for custom data exporting."""

from collections import OrderedDict
from typing import Optional, Union

from jinja2 import Template

from django.contrib.auth.models import User
from django.db.models import QuerySet

from rest_framework import serializers, views

from common.models import DataOutput
from common.settings import get_global_setting
from InvenTree.helpers import current_date
from plugin import PluginMixinEnum


class DataExportMixin:
    """Mixin which provides ability to customize data exports.

    When exporting data from the API, this mixin can be used to provide
    custom data export functionality.
    """

    ExportOptionsSerializer = None

    class MixinMeta:
        """Meta options for this mixin."""

        MIXIN_NAME = 'DataExport'

    def __init__(self):
        """Register mixin."""
        super().__init__()
        self.add_mixin(PluginMixinEnum.EXPORTER, True, __class__)

    def supports_export(
        self,
        model_class: type,
        user: User,
        serializer_class: Optional[serializers.Serializer] = None,
        view_class: Optional[views.APIView] = None,
        *args,
        **kwargs,
    ) -> bool:
        """Return True if this plugin supports exporting data for the given model.

        Args:
            model_class: The model class to check
            user: The user requesting the export
            serializer_class: The serializer class to use for exporting the data
            view_class: The view class to use for exporting the data

        Returns:
            True if the plugin supports exporting data for the given model
        """
        # By default, plugins support all models
        return True

    DEFAULT_FILENAME_TEMPLATE = 'InvenTree_{{ model }}_{{ date }}'

    @staticmethod
    def _sanitize_filename_component(value: str) -> str:
        """Return a filesystem-safe filename component."""

        filename = str(value or '').strip()

        for char in ['\\', '/', '\n', '\r', '\t', '\x00']:
            filename = filename.replace(char, '_')

        return filename.rstrip('.')

    def generate_filename(
        self,
        model_class,
        export_format: str,
        context: Optional[dict] = None,
    ) -> str:
        """Generate a filename for the exported data."""

        model_name = getattr(model_class, '__name__', 'Data')

        meta = getattr(model_class, '_meta', None)
        verbose_name = getattr(meta, 'verbose_name', model_name) if meta else model_name
        verbose_name_plural = (
            getattr(meta, 'verbose_name_plural', verbose_name) if meta else verbose_name
        )

        base_context = {
            'model': model_name,
            'model_verbose_name': verbose_name,
            'model_verbose_name_plural': verbose_name_plural,
            'date': current_date().isoformat(),
            'export_format': export_format,
        }

        if context:
            base_context.update(context)

        template_string = get_global_setting(
            'DATA_EXPORT_FILENAME_TEMPLATE',
            backup_value=self.DEFAULT_FILENAME_TEMPLATE,
        )

        filename_root = ''

        try:
            filename_root = Template(str(template_string)).render(base_context).strip()
        except Exception:
            filename_root = ''

        filename_root = self._sanitize_filename_component(filename_root)

        if not filename_root:
            fallback = f'InvenTree_{model_name}_{base_context["date"]}'
            filename_root = self._sanitize_filename_component(fallback)

        extension = f'.{export_format}'

        if filename_root.lower().endswith(extension.lower()):
            return filename_root

        return f'{filename_root}{extension}'

    def update_headers(
        self, headers: OrderedDict, context: dict, **kwargs
    ) -> OrderedDict:
        """Update the headers for the data export.

        Allows for optional modification of the headers for the data export.

        Arguments:
            headers: The current headers for the export
            context: The context for the export (provided by the plugin serializer)

        Returns: The updated headers
        """
        # The default implementation does nothing
        return headers

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        """Filter the queryset before exporting data."""
        # The default implementation returns the queryset unchanged
        return queryset

    def export_data(
        self,
        queryset: QuerySet,
        serializer_class: serializers.Serializer,
        headers: OrderedDict,
        context: dict,
        output: DataOutput,
        **kwargs,
    ) -> list:
        """Export data from the queryset.

        This method should be implemented by the plugin to provide
        the actual data export functionality.

        Arguments:
            queryset: The queryset to export
            serializer_class: The serializer class to use for exporting the data
            headers: The headers for the export
            context: Any custom context for the export (provided by the plugin serializer)
            output: The DataOutput object for the export

        Returns: The exported data (a list of dict objects)
        """
        # The default implementation simply serializes the queryset
        return serializer_class(queryset, many=True, exporting=True).data

    def get_export_options_serializer(
        self, **kwargs
    ) -> Union[serializers.Serializer, None]:
        """Return a serializer class with dynamic export options for this plugin.

        Returns:
            A class instance of a DRF serializer class, by default this an instance of
            self.ExportOptionsSerializer using the *args, **kwargs if existing for this plugin
        """
        # By default, look for a class level attribute
        serializer = getattr(self, 'ExportOptionsSerializer', None)

        if serializer:
            return serializer(**kwargs)
