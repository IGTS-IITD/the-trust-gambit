import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRoundGraph } from "../api.js";
import cytoscape from "cytoscape";
import {
  EmptyState,
  Loading,
  Notice,
  PageHeader,
  Panel,
  initials,
} from "../components/UI.jsx";

function buildElements(data) {
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

  const missing = new Set();
  for (const ed of edges) {
    if (!nodeIds.has(ed.data.source)) missing.add(ed.data.source);
    if (!nodeIds.has(ed.data.target)) missing.add(ed.data.target);
  }

  const placeholderNodes = Array.from(missing).map((id) => ({
    data: { id, label: id, placeholder: true },
  }));

  return [...nodes, ...placeholderNodes, ...edges];
}

const cytoscapeStyle = [
  {
    selector: "node",
    style: {
      "background-color": "#e8f2ed",
      "border-color": "#166b58",
      "border-width": 1.5,
      label: "data(label)",
      color: "#17212c",
      "font-size": 11,
      "font-family": "Inter, 'Segoe UI', Arial, sans-serif",
      "font-weight": 600,
      "text-valign": "center",
      "text-halign": "center",
      shape: "round-rectangle",
      padding: "10px",
      width: "label",
      height: "label",
      "text-wrap": "wrap",
      "text-max-width": 120,
    },
  },
  {
    selector: "node[placeholder]",
    style: {
      "background-color": "#fff1ee",
      "border-color": "#a33932",
      "border-style": "dashed",
      color: "#a33932",
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.5,
      "line-color": "#b9c1c6",
      "target-arrow-color": "#66717c",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
    },
  },
  {
    selector: ":selected",
    style: {
      "background-color": "#166b58",
      color: "#fff",
      "line-color": "#166b58",
      "target-arrow-color": "#166b58",
    },
  },
];

const layoutOptions = {
  name: "breadthfirst",
  directed: true,
  padding: 10,
  spacingFactor: 1.2,
  animate: true,
  fit: true,
};

export default function RoundGraph() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const containerRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError("");

    apiRoundGraph(id)
      .then((response) => {
        if (!cancelled) setData(response);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Unable to load the delegation graph.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!containerRef.current || !data) return;

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const elements = buildElements(data);

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: cytoscapeStyle,
      layout: layoutOptions,
      wheelSensitivity: 0.2,
    });

    cyRef.current.fit();

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
    cyRef.current.layout(layoutOptions).run();
    cyRef.current.fit();
  };

  const fitView = () => cyRef.current?.fit();

  const zoomIn = () =>
    cyRef.current?.zoom({ level: cyRef.current.zoom() * 1.2 });

  const zoomOut = () =>
    cyRef.current?.zoom({ level: cyRef.current.zoom() / 1.2 });

  const nodesCount = data?.nodes?.length ?? 0;
  const edgesCount = data?.edges?.length ?? 0;
  const nodeList = useMemo(
    () => (Array.isArray(data?.nodes) ? data.nodes : []),
    [data]
  );
  const edgeList = useMemo(
    () => (Array.isArray(data?.edges) ? data.edges : []),
    [data]
  );

  return (
    <>
      <PageHeader
        eyebrow="Delegation map"
        title="Graph view."
        description="Inspect how participants delegated their decisions in this round."
        actions={
          <Link className="btn" to="/rounds">
            ← All rounds
          </Link>
        }
      />

      {loading ? (
        <Loading label="Loading delegation graph" />
      ) : error ? (
        <Notice tone="error">{error}</Notice>
      ) : !data ? (
        <Panel>
          <EmptyState
            title="No graph data."
            description="The delegation graph for this round is not available."
          />
        </Panel>
      ) : (
        <div className="stack">
          <div className="metrics" style={{ marginBottom: 0 }}>
            <div className="metric">
              <div className="metric-label">Participants</div>
              <div className="metric-value mono">{nodesCount}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Delegations</div>
              <div className="metric-value mono">{edgesCount}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Controls</div>
              <div className="button-row" style={{ marginTop: 4 }}>
                <button type="button" className="btn" onClick={runLayout}>
                  Layout
                </button>
                <button type="button" className="btn" onClick={fitView}>
                  Fit
                </button>
                <button type="button" className="btn" onClick={zoomIn}>
                  +
                </button>
                <button type="button" className="btn" onClick={zoomOut}>
                  −
                </button>
              </div>
            </div>
          </div>

          <Panel>
            <div className="graph-layout">
              <div
                ref={containerRef}
                className="graph-canvas"
                role="img"
                aria-label={`Delegation graph with ${nodesCount} participants and ${edgesCount} delegations`}
              />

              <div className="graph-sidebar">
                <p className="eyebrow">Participants</p>

                {nodeList.length === 0 ? (
                  <p className="small muted">None listed.</p>
                ) : (
                  <ul className="graph-list">
                    {nodeList.map((n) => {
                      const label = n?.data?.label ?? String(n.id);
                      return (
                        <li key={n.id}>
                          <div className="person">
                            <span className="avatar" aria-hidden="true">
                              {initials(label)}
                            </span>
                            <span className="person-name small">
                              {label}
                            </span>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}

                <p className="eyebrow" style={{ marginTop: 16 }}>
                  Delegations
                </p>

                {edgeList.length === 0 ? (
                  <p className="small muted">No delegations in this round.</p>
                ) : (
                  <ul className="graph-list">
                    {edgeList.map((e) => (
                      <li key={e.id} className="mono small">
                        {e.source} → {e.target}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="graph-legend">
              <span>
                <span
                  style={{
                    display: "inline-block",
                    width: 10,
                    height: 10,
                    background: "#e8f2ed",
                    border: "1.5px solid #166b58",
                    borderRadius: 2,
                    marginRight: 6,
                    verticalAlign: "middle",
                  }}
                />
                Node
              </span>
              <span>
                <span
                  style={{
                    display: "inline-block",
                    width: 10,
                    height: 10,
                    background: "#fff1ee",
                    border: "1.5px dashed #a33932",
                    borderRadius: 2,
                    marginRight: 6,
                    verticalAlign: "middle",
                  }}
                />
                Placeholder
              </span>
              <span>
                <span
                  style={{
                    display: "inline-block",
                    width: 16,
                    height: 1.5,
                    background: "#b9c1c6",
                    marginRight: 6,
                    verticalAlign: "middle",
                  }}
                />
                Delegation edge
              </span>
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}
