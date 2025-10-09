
# InvenTree Product Tree Plugin

Visualize a part's BOM hierarchy as a clickable graph using Mermaid.

## Install (Docker)
1. Copy the folder `product_tree/` to your plugin directory (e.g. `/inventree-data/plugins/product_tree/`).
2. Ensure plugins are enabled and the plugin dir is configured.
3. Restart InvenTree.
4. In *Admin → Plugins*, enable **Product Tree (BOM graph)**.

## URLs
- Navigation → Product Tree
- Direct: `/plugin/product_tree/tree/<part_id>/`
- JSON: `/plugin/product_tree/api/tree/<part_id>/?max_depth=10`

## Notes
- Mermaid is loaded via CDN. If your server has no internet access, bundle mermaid locally and change the script tag in `templates/product_tree/tree.html`.
