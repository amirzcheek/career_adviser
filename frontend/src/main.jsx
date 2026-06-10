import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import App from "./App.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import InterviewPage from "./pages/InterviewPage.jsx";
import "./index.css";

// Маршруты: App — общий layout (шапка + <Outlet/>).
const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <ChatPage /> },
      { path: "interview", element: <InterviewPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
