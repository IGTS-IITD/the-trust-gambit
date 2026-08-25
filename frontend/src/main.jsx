import React, { Suspense, lazy } from "react"
import { createRoot } from "react-dom/client"
import { createBrowserRouter, RouterProvider } from "react-router-dom"
import "./styles/index.css"
import App from "./App.jsx"
import Login from "./pages/Login.jsx"
import Register from "./pages/Register.jsx"
import Dashboard from "./pages/Dashboard.jsx"
import Profile from "./pages/Profile.jsx"
import Leaderboard from "./pages/Leaderboard.jsx"
import Rounds from "./pages/Rounds.jsx"
import SelfRatings from "./pages/SelfRatings.jsx"

// Cytoscape is a large dependency only needed on this one page, so it's
// split into its own chunk and fetched on demand instead of bloating the
// initial bundle every mobile user has to download.
const RoundGraph = lazy(() => import("./pages/RoundGraph.jsx"))

const graphFallback = (
  <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
    <div className="space-y-3 animate-pulse">
      <div className="h-12 bg-slate-100 rounded-lg" />
      <div className="h-[50vh] bg-slate-100 rounded-lg" />
    </div>
  </div>
)

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "login", element: <Login /> },
      { path: "register", element: <Register /> },
      { path: "profile", element: <Profile /> },
      { path: "leaderboard", element: <Leaderboard /> },
      { path: "rounds", element: <Rounds /> },
      {
        path: "rounds/:id/graph",
        element: (
          <Suspense fallback={graphFallback}>
            <RoundGraph />
          </Suspense>
        ),
      },
      { path: "self-ratings", element: <SelfRatings /> },
    ],
  },
])

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
