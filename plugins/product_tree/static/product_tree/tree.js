
// Minimal helper to render a hierarchical JSON tree using Mermaid (graph TD)
window.ProductTree = (function(){
  function escape(s){
    return String(s || '').replace(/"/g, '\"').replace(/\[/g, '(').replace(/\]/g, ')');
  }

  function buildMermaid(node){
    const lines = ['graph TD'];
    const seen = new Set();

    function nodeLabel(n){
      const name = n.name || '(unnamed)';
      const ipn = n.ipn ? `\nIPN: ${n.ipn}` : '';
      const cycle = n.cycle ? '\n↻ cycle' : '';
      const substitutes = Array.isArray(n.substitutes) && n.substitutes.length
        ? `\nSubs: ${n.substitutes.map(s => s.name || s.ipn || s.id).join(', ')}`
        : '';
      return `${name}${ipn}${substitutes}${cycle}`;
    }

    function id(n){ return `P${n.id}`; }

    function walk(n){
      if(!n || !n.id) return;
      if(!seen.has(n.id)){
        lines.push(`${id(n)}["${escape(nodeLabel(n))}"]`);
        seen.add(n.id);
      }
      (n.children || []).forEach(child => {
        if(!child || !child.id){ return; }

        const qty = (child.quantity != null) ? `|${child.quantity}|` : '';
        const connector = child.cycle ? '-.->' : '-->';
        lines.push(`${id(n)} ${connector}${qty} ${id(child)}`);

        if(!child.cycle){
          walk(child);
        }
      });
    }
    walk(node);
    return lines.join('\n');
  }

  async function renderMermaidFromEndpoint(url, graphId, errorId){
    const graph = document.getElementById(graphId);
    const err = document.getElementById(errorId);
    if(err) err.textContent = '';
    try{
      const res = await fetch(url, {credentials: 'same-origin'});
      if(!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const def = buildMermaid(data);
      if(window.mermaid){
        window.mermaid.render('ptree', def).then(({svg}) => {
          graph.innerHTML = svg;
        }).catch(e => {
          graph.textContent = def;
          if(err) err.textContent = String(e);
        });
      }else{
        graph.textContent = def;
      }
    }catch(e){
      if(err) err.textContent = String(e);
    }
  }

  return { renderMermaidFromEndpoint };
})();
