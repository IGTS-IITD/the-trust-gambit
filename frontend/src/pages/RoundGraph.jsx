import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { apiRoundGraph } from "../api.js";
import cytoscape from "cytoscape";

export default function RoundGraph() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const containerRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    setLoading(true);
    apiRoundGraph(id)
      .then(setData)
      .catch((e) => setError(e.message || "Failed to load graph"))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!containerRef.current || !data) return;

    // Destroy previous instance if re-rendering with new data
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    // Normalize and sanitize graph data
    const rawNodes = Array.isArray(data.nodes) ? data.nodes : [];
    const nodes = rawNodes.map((n) => ({
      data: {
        id: String(n.id),
        label: n?.data?.label ?? String(n.id),
      },
    }));
    const nodeIds = new Set(nodes.map((n) => n.data.id));

    const rawEdges = Array.isArray(data.edges) ? data.edges : [];
    const edges = rawEdges.map((e, idx) => ({
      data: {
        id: String(e.id ?? `e-${e.source}-${e.target}-${idx}`),
        source: String(e.source),
        target: String(e.target),
      },
    }));

    // Create placeholder nodes for any missing endpoints to prevent Cytoscape errors
    const missing = new Set();
    for (const ed of edges) {
      if (!nodeIds.has(ed.data.source)) missing.add(ed.data.source);
      if (!nodeIds.has(ed.data.target)) missing.add(ed.data.target);
    }
    const placeholderNodes = Array.from(missing).map((id) => ({
      data: { id, label: id, placeholder: true },
    }));

    const elements = [...nodes, ...placeholderNodes, ...edges];

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#3b82f6",
            "border-color": "#1e3a8a",
            "border-width": 1,
            label: "data(label)",
            color: "#0f172a",
            "font-size": 12,
            "text-valign": "center",
            "text-halign": "center",
            shape: "round-rectangle",
            padding: "8px",
            width: "label",
            height: "label",
            "text-wrap": "wrap",
            "text-max-width": 120,
          },
        },
        {
          selector: "node[placeholder]",
          style: {
            "background-color": "#fde68a",
            "border-color": "#f59e0b",
            "border-style": "dashed",
            color: "#7c2d12",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#9ca3af",
            "target-arrow-color": "#9ca3af",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        {
          selector: ":selected",
          style: {
            "background-color": "#2563eb",
            "line-color": "#2563eb",
            "target-arrow-color": "#2563eb",
          },
        },
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        padding: 10,
        spacingFactor: 1.2,
        animate: true,
        fit: true,
      },
      wheelSensitivity: 0.2,
    });

    // Keep graph fitting on first render
    cyRef.current.fit();

    // Resize handler to keep it fitting when the container changes size
    const onResize = () => {
      if (!cyRef.current) return;
      cyRef.current.resize();
      cyRef.current.fit();
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [data]);

  const runLayout = () => {
    if (!cyRef.current) return;
    cyRef.current
      .layout({
        name: "breadthfirst",
        directed: true,
        fit: true,
        padding: 10,
        spacingFactor: 1.2,
        animate: true,
      })
      .run();
    cyRef.current.fit();
  };
  const fitView = () => cyRef.current?.fit();
  const zoomIn = () =>
    cyRef.current?.zoom({ level: cyRef.current.zoom() * 1.2 });
  const zoomOut = () =>
    cyRef.current?.zoom({ level: cyRef.current.zoom() / 1.2 });

  const nodesCount = data?.nodes?.length || 0;
  const edgesCount = data?.edges?.length || 0;

  if (loading)
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🕸️</span>
          <h1 className="text-xl font-semibold text-slate-800">
            Delegation Graph
          </h1>
        </div>
        <div className="space-y-3 animate-pulse">
          <div className="h-12 bg-slate-100 rounded-lg" />
          <div className="h-[50vh] bg-slate-100 rounded-lg" />
        </div>
      </div>
    );

  if (error)
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
        <strong>Error:</strong> {error}
      </div>
    );

  if (!data)
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
        <div className="text-slate-600">No graph data.</div>
      </div>
    );

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-700 grid place-items-center border border-indigo-100">
            🕸️
          </div>
          <h1 className="text-xl font-semibold text-slate-800">
            Delegation Graph
          </h1>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 border border-slate-200">
            <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />{" "}
            {nodesCount} nodes
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 border border-slate-200">
            <span className="w-2 h-2 rounded-full bg-slate-400 inline-block" />{" "}
            {edgesCount} edges
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={runLayout}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:shadow-sm active:scale-95 transition-all"
        >
          Auto layout
        </button>
        <button
          onClick={fitView}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:shadow-sm active:scale-95 transition-all"
        >
          Fit
        </button>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={zoomOut}
            className="w-9 h-9 grid place-items-center rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:shadow-sm active:scale-95 transition-all"
          >
            −
          </button>
          <button
            onClick={zoomIn}
            className="w-9 h-9 grid place-items-center rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:shadow-sm active:scale-95 transition-all"
          >
            +
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="md:col-span-2">
          <div
            ref={containerRef}
            className="h-[60vh] md:h-[65vh] w-full rounded-lg border border-slate-200 bg-gradient-to-br from-slate-50 to-white"
          />
          <div className="mt-3 flex items-center gap-3 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-blue-500 inline-block border border-blue-900/30" />{" "}
              Node
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-amber-300 inline-block border border-amber-500/50" />{" "}
              Placeholder
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-6 h-[2px] bg-slate-400 inline-block" /> Edge
            </span>
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Participants
            </h2>
            {data.nodes?.length ? (
              <ul className="space-y-1 max-h-[28rem] overflow-auto pr-1">
                {data.nodes.map((n) => (
                  <li
                    key={n.id}
                    className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700"
                  >
                    <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 grid place-items-center text-xs border border-blue-200">
                      {(n.data?.label ?? String(n.id))
                        .slice(0, 2)
                        .toUpperCase()}
                    </span>
                    <span className="truncate">{n.data?.label ?? n.id}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-sm text-slate-500">No participants.</div>
            )}
          </div>
          <div>
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Delegations
            </h2>
            {data.edges?.length ? (
              <ul className="space-y-1 max-h-[28rem] overflow-auto pr-1">
                {data.edges.map((e) => (
                  <li
                    key={e.id}
                    className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700"
                  >
                    <span className="font-mono bg-slate-100 border border-slate-200 rounded px-1.5 py-0.5">
                      {e.source}
                    </span>
                    <span className="text-slate-400">→</span>
                    <span className="font-mono bg-slate-100 border border-slate-200 rounded px-1.5 py-0.5">
                      {e.target}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-sm text-slate-500">No delegations.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
