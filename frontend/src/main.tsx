import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import "./index.css";
import Login from "./pages/Login";
import Feed from "./pages/Feed";
import Collection from "./pages/Collection";
import RecordDetail from "./pages/RecordDetail";
import DMs from "./pages/DMs";
import AppShell from "./layouts/AppShell";
import { useAuth } from "./store/auth";
import AppError from "./components/AppError";

const qc = new QueryClient();


function Protected({ children }: { children: React.ReactNode }) {
  const token = useAuth((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}


const router = createBrowserRouter([
  { path: "/login", element: <Login />, errorElement: <AppError /> },
  {
    path: "/",
    element: <Protected><AppShell /></Protected>,
    errorElement: <AppError />,
    children: [
      { index: true, element: <Feed /> },
      { path: "collection", element: <Collection /> },
      { path: "record/:id", element: <RecordDetail /> },
      { path: "dms", element: <DMs /> },
    ],
  },
]);


ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);