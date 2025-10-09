
# -*- coding: utf-8 -*-
"""
InvenTree plugin: Product Tree visualizer
- Adds a page that renders a product/BOM hierarchy as a graph
- Provides a JSON endpoint for BOM tree data
"""
from plugin import InvenTreePlugin
from plugin.mixins import UrlsMixin, NavigationMixin
from django.urls import path
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator

from part.models import Part, BomItem

class ProductTreePlugin(UrlsMixin, NavigationMixin, InvenTreePlugin):
    NAME = "ProductTreePlugin"
    SLUG = "product_tree"
    TITLE = "Product Tree (BOM graph)"
    DESCRIPTION = "Visualize a part's BOM hierarchy as an interactive graph"
    VERSION = "0.1.0"
    AUTHOR = "ChatGPT"
    PUBLISH_DATE = "2025-10-09"

    # Add a nav item that links to our landing page (template provides picker / docs)
    NAVIGATION = [
        {"name": "Product Tree", "link": "product-tree-home", "icon": "fa-sitemap"}
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
    def view_tree(request, pk: int):
        """
        Page that renders the graph for a given part (pk).
        """
        try:
            part = Part.objects.get(pk=pk)
        except Part.DoesNotExist:
            return HttpResponse("Part not found", status=404)

        ctx = {"part": part}
        return render(request, "product_tree/tree.html", ctx)

    # ---- API ----
    @staticmethod
    @login_required
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
        try:
            max_depth = int(request.GET.get("max_depth", 10))
        except Exception:
            max_depth = 10

        def build_node(p: Part, depth: int):
            node = {
                "id": p.pk,
                "name": p.name,
                "ipn": getattr(p, "IPN", None),
                "assembly": bool(getattr(p, "assembly", False)),
                "revision": getattr(p, "revision", None),
                "children": [],
            }
            if depth >= max_depth:
                return node

            # Fetch BOM items where this part is the parent
            bom_items = BomItem.objects.filter(part=p).select_related("sub_part")
            for bi in bom_items:
                sp = bi.sub_part
                child = {
                    "id": sp.pk if sp else None,
                    "name": sp.name if sp else "(missing)",
                    "ipn": getattr(sp, "IPN", None) if sp else None,
                    "assembly": bool(getattr(sp, "assembly", False)) if sp else False,
                    "quantity": float(bi.quantity) if bi.quantity is not None else None,
                    "reference": bi.reference,
                    "note": bi.note,
                    "children": [],
                }
                # Recurse only if sub_part exists and is assembly-like
                if sp and getattr(sp, "assembly", False):
                    child = build_node(sp, depth + 1) | {
                        "quantity": float(bi.quantity) if bi.quantity is not None else None,
                        "reference": bi.reference,
                        "note": bi.note,
                    }
                node["children"].append(child)
            return node

        data = build_node(part, depth=0)
        return JsonResponse(data, safe=False)
