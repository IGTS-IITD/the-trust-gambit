import React from "react"
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
import RoundGraph from "./pages/RoundGraph.jsx"
import SelfRatings from "./pages/SelfRatings.jsx"

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
      { path: "rounds/:id/graph", element: <RoundGraph /> },
      { path: "self-ratings", element: <SelfRatings /> },
    ],
  },
])

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
