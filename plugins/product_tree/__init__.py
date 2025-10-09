
# -*- coding: utf-8 -*-
"""
InvenTree plugin: Product Tree visualizer
- Adds a page that renders a product/BOM hierarchy as a graph
- Provides a JSON endpoint for BOM tree data
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, Iterable, List, MutableMapping, Set

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import path

from plugin import InvenTreePlugin
from plugin.mixins import NavigationMixin, UrlsMixin

from part.models import BomItem, Part


def _decimal_to_float(value: Decimal | None) -> float | None:
    """Convert a Decimal to a float while keeping ``None`` values intact."""

    if value is None:
        return None

    return float(value)


def _truthy(value: str | None, *, default: bool = False) -> bool:
    """Return ``True`` when *value* represents an affirmative flag."""

    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "y", "on"}


class ProductTreePlugin(UrlsMixin, NavigationMixin, InvenTreePlugin):
    NAME = "ProductTreePlugin"
    SLUG = "product_tree"
    TITLE = "Product Tree (BOM graph)"
    DESCRIPTION = "Visualize a part's BOM hierarchy as an interactive graph"
    VERSION = "0.2.0"
    AUTHOR = "ChatGPT"
    PUBLISH_DATE = "2025-10-09"

    DEFAULT_MAX_DEPTH = 10
    ABSOLUTE_MAX_DEPTH = 25

    # Add a nav item that links to our landing page (template provides picker / docs)
    NAVIGATION = [
        {
            "name": "Product Tree",
            "link": "plugin:product_tree:product-tree-home",
            "icon": "fa-sitemap",
        }
    ]

    # ---- URLS ----
    def setup_urls(self):
        """
        Register our page and API endpoints.
        """
        return [
            path("tree/", self.view_home, name="product-tree-home"),
            path("tree/<int:pk>/", self.view_tree, name="product-tree-detail"),
            path("api/tree/<int:pk>/", self.api_tree, name="product-tree-data"),
        ]

    # ---- VIEWS ----
    @staticmethod
    @login_required
    def view_home(request):
        """
        Landing page with a simple search box / instructions.
        """
        return render(request, "product_tree/home.html", {})

    @staticmethod
    @login_required
    @permission_required("part.view_part", raise_exception=True)
    def view_tree(request, pk: int):
        """
        Page that renders the graph for a given part (pk).
        """
        try:
            part = Part.objects.get(pk=pk)
        except Part.DoesNotExist:
            return HttpResponse("Part not found", status=404)

        ctx = {
            "part": part,
            "default_max_depth": ProductTreePlugin.DEFAULT_MAX_DEPTH,
            "max_depth_limit": ProductTreePlugin.ABSOLUTE_MAX_DEPTH,
        }
        return render(request, "product_tree/tree.html", ctx)

    # ---- API ----
    @staticmethod
    @login_required
    @permission_required("part.view_part", raise_exception=True)
    def api_tree(request, pk: int):
        """
        Return a nested JSON tree for the BOM of the given part.
        Optional query params:
          - max_depth (int): recursion limit (default 10)
          - include_substitutes (bool): include substitutes (default false; placeholder)
          - collapse_single (bool): collapse single-child chains (default false; done client-side typically)
        """
        try:
            part = Part.objects.get(pk=pk)
        except Part.DoesNotExist:
            return JsonResponse({"error": "Part not found"}, status=404)

        # parse params
        raw_max_depth = request.GET.get("max_depth")
        max_depth = ProductTreePlugin.DEFAULT_MAX_DEPTH
        if raw_max_depth is not None:
            try:
                max_depth = int(raw_max_depth)
            except (TypeError, ValueError):
                max_depth = ProductTreePlugin.DEFAULT_MAX_DEPTH

        max_depth = max(0, min(max_depth, ProductTreePlugin.ABSOLUTE_MAX_DEPTH))

        include_substitutes = _truthy(request.GET.get("include_substitutes"))

        bom_cache: MutableMapping[int, List[BomItem]] = defaultdict(list)

        def get_bom_items(parent: Part) -> Iterable[BomItem]:
            """Retrieve cached BOM items for *parent*."""

            if parent.pk not in bom_cache:
                bom_cache[parent.pk] = list(
                    BomItem.objects.filter(part=parent)
                    .select_related("sub_part")
                    .prefetch_related("substitutes__part")
                )

            return bom_cache[parent.pk]

        def build_node(p: Part, depth: int, ancestors: Set[int]):
            node: Dict[str, Any] = {
                "id": p.pk,
                "name": p.name,
                "ipn": getattr(p, "IPN", None),
                "assembly": bool(getattr(p, "assembly", False)),
                "revision": getattr(p, "revision", None),
                "url": p.get_absolute_url(),
                "children": [],
            }

            if depth >= max_depth:
                return node

            next_ancestors = set(ancestors)
            next_ancestors.add(p.pk)

            for bi in get_bom_items(p):
                sp = bi.sub_part
                child: Dict[str, Any] = {
                    "id": sp.pk if sp else None,
                    "name": sp.name if sp else "(missing)",
                    "ipn": getattr(sp, "IPN", None) if sp else None,
                    "assembly": bool(getattr(sp, "assembly", False)) if sp else False,
                    "quantity": _decimal_to_float(bi.quantity),
                    "reference": bi.reference,
                    "note": bi.note,
                    "url": sp.get_absolute_url() if sp else None,
                    "children": [],
                }

                if sp:
                    if sp.pk in next_ancestors:
                        child["cycle"] = True
                    elif getattr(sp, "assembly", False):
                        subtree = build_node(sp, depth + 1, next_ancestors)
                        subtree.update(
                            {
                                "quantity": _decimal_to_float(bi.quantity),
                                "reference": bi.reference,
                                "note": bi.note,
                            }
                        )
                        child = subtree

                    if include_substitutes:
                        substitutes = [
                            {
                                "id": sub.part.pk,
                                "name": sub.part.name,
                                "ipn": getattr(sub.part, "IPN", None),
                                "url": sub.part.get_absolute_url(),
                            }
                            for sub in bi.substitutes.all()
                        ]

                        if substitutes:
                            child["substitutes"] = substitutes

                node["children"].append(child)

            return node

        data = build_node(part, depth=0, ancestors=set())
        return JsonResponse(data)
