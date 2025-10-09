"""Assembly hierarchy visualization plugin for InvenTree."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from part.models import BomItem, Part
from plugin import InvenTreePlugin
from plugin.mixins import NavigationMixin, UrlsMixin, UserInterfaceMixin



@dataclass
class TreeNode:
    """Container representing a single BOM node in the rendered tree."""

    item: BomItem
    children: list['TreeNode']
    cycle: bool = False

    @property
    def sub_part(self) -> Part:
        return self.item.sub_part


class AssemblyHierarchyPlugin(
    UserInterfaceMixin, NavigationMixin, UrlsMixin, InvenTreePlugin
):
    """Plugin which renders the full BOM hierarchy for an assembly part."""

    NAME = 'Assembly Hierarchy'
    SLUG = 'assembly-hierarchy'
    TITLE = _('Assembly Hierarchy Viewer')
    DESCRIPTION = _(
        'Visualise the complete Bill of Materials hierarchy for any assembly part.'
    )
    VERSION = '1.1'

    NAVIGATION = [
        {
            'name': _('Assembly hierarchy'),
            'link': 'plugin:assembly-hierarchy:index',
            'icon': 'fas fa-sitemap',
        }
    ]

    def get_ui_panels(self, request, context, **kwargs):
        """Expose the hierarchy viewer as a panel on the part detail page."""

        context = context or {}
        target_model = context.get('target_model')
        target_id = context.get('target_id')

        if target_model != 'part' or target_id is None:
            return []

        try:
            part_id = int(target_id)
        except (TypeError, ValueError):
            return []

        try:
            part = Part.objects.get(pk=part_id)
        except Part.DoesNotExist:
            return []

        detail_url = reverse(
            'plugin:assembly-hierarchy:assembly-detail',
            kwargs={'pk': part.pk},
        )

        return [
            {
                'key': 'assembly-hierarchy-panel',
                'title': _('Assembly hierarchy'),
                'icon': 'fa6-solid:sitemap',
                'source': self.plugin_static_file('panel.js'),
                'context': {
                    'detail_url': detail_url,
                    'index_url': reverse('plugin:assembly-hierarchy:index'),
                    'is_assembly': part.assembly,
                    'has_bom': part.has_bom,
                    'part_name': part.full_name,
                },
            }
        ]

    def get_ui_navigation_items(self, request, context, **kwargs):
        """Expose a navigation tab entry for the React interface."""

        target_url = reverse('plugin:assembly-hierarchy:index')

        if isinstance(context, dict):
            part_id = None

            if context.get('model') == 'part' and context.get('pk') is not None:
                part_id = context.get('pk')
            elif context.get('part') is not None:
                part_id = context.get('part')

            try:
                part_id_int = int(part_id) if part_id is not None else None
            except (TypeError, ValueError):
                part_id_int = None

            if part_id_int:
                target_url = reverse(
                    'plugin:assembly-hierarchy:assembly-detail',
                    kwargs={'pk': part_id_int},
                )

        return [
            {
                'key': 'assembly-hierarchy-navigation',
                'title': _('Assembly hierarchy'),
                'icon': 'fa6-solid:sitemap',
                'options': {
                    'url': target_url,
                },
            }
        ]

    def setup_urls(self):  # pragma: no cover - url wiring tested via framework
        return [
            path('', self.index_view, name='index'),
            path('assembly/<int:pk>/', self.hierarchy_view, name='assembly-detail'),
        ]

    # region views
    def index_view(self, request: HttpRequest) -> HttpResponse:
        """Landing page where the user can choose an assembly to inspect."""

        assemblies = (
            Part.objects.filter(assembly=True)
            .order_by('name')
            .only('id', 'name', 'description', 'revision')[:25]
        )

        error_message: str | None = None
        query = request.GET.get('part')

        if query:
            try:
                part_id = int(query)
                part = Part.objects.get(pk=part_id)
                return redirect(
                    reverse(
                        'plugin:assembly-hierarchy:assembly-detail',
                        kwargs={'pk': part.pk},
                    )
                )
            except (ValueError, Part.DoesNotExist):
                error_message = _('Kon het onderdeel met dit ID niet vinden.')

        context = {
            'assemblies': assemblies,
            'error': error_message,
        }

        return render(request, 'assembly_hierarchy/index.html', context)

    def hierarchy_view(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Display the recursive hierarchy for the selected assembly."""

        part = get_object_or_404(Part, pk=pk)

        tree = self._build_tree(part, path=set())
        depth, total_nodes = self._collect_metrics(tree)

        context = {
            'part': part,
            'tree': tree,
            'depth': depth,
            'total_nodes': total_nodes,
        }

        if not part.assembly:
            context['warning'] = _(
                'Dit onderdeel is niet gemarkeerd als assembly maar kan wel een stuklijst hebben.'
            )

        embed_mode = request.GET.get('embed') == '1'
        template_name = 'assembly_hierarchy/hierarchy.html'

        if embed_mode:
            template_name = 'assembly_hierarchy/panel.html'

        context['embed'] = embed_mode

        return render(request, template_name, context)

    # endregion

    # region helpers
    def _build_tree(self, part: Part, path: set[int]) -> list[TreeNode]:
        """Recursively build the BOM tree for ``part``."""

        nodes: list[TreeNode] = []

        current_path = set(path)
        current_path.add(part.pk)

        bom_items = (
            BomItem.objects.filter(part=part)
            .select_related('sub_part')
            .order_by('sub_part__name')
        )

        for item in bom_items:
            sub_part = item.sub_part
            cycle_detected = sub_part.pk in current_path

            if cycle_detected:
                node = TreeNode(item=item, children=[], cycle=True)
            else:
                node = TreeNode(
                    item=item,
                    children=self._build_tree(sub_part, current_path),
                    cycle=False,
                )

            nodes.append(node)

        return nodes

    def _collect_metrics(self, nodes: Iterable[TreeNode], depth: int = 0) -> tuple[int, int]:
        """Return the (max_depth, total_node_count) for the provided nodes."""

        max_depth = depth
        count = 0

        for node in nodes:
            count += 1
            child_depth, child_count = self._collect_metrics(node.children, depth + 1)
            count += child_count
            max_depth = max(max_depth, child_depth)

        return max_depth, count

    # endregion


__all__ = ['AssemblyHierarchyPlugin']
