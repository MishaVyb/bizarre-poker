import { createBrowserRouter, Navigate } from "react-router-dom";

import Root from "./Root";
import GamePage from "./GamePage";
import About from "./About";
import ErrorPage from "./ErrorPage";
import GameListPage from "./GameListPage";
import GameService from "./../services/GameService";
import Login from "./Login";
import { useContext } from "react";
import { AuthContext } from "../context";
import Logout from "./Logout";
import MePage from "./MePage";
import AuthService from "../services/AuthService";

const AuthRequired = ({ children }) => {
  const { auth } = useContext(AuthContext);
  if (!auth) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

export const getRouter_fake = (authService, gameService) => {
  return createBrowserRouter([
    {
      path: "/",
      element: <Root />,
      errorElement: <ErrorPage />,
      children: [

      ],
    },
  ]);
};

export const getRouter = (authService, gameService) => {
  // make sure that all methods for services are bounded (!)
  return createBrowserRouter([
    {
      path: "/",
      element: <Root />,
      errorElement: <ErrorPage />,
      children: [
        {
          path: "/",
          element: <GameListPage />,
          loader: gameService.getAll,
        },
        {
          path: "games/:gameId",
          element: (
            <AuthRequired>
              <GamePage />
            </AuthRequired>
          ),
          loader: async ({ params }) => {
            return fetch(`/api/teams/${params.gameId}.json`);
          },
        },
        {
          path: "login",
          element: <Login />,
        },
        {
          path: "logout",
          element: <Logout />,
        },
        {
          path: "me",
          element: (
            <AuthRequired>
              <MePage />
            </AuthRequired>
          ),
          loader: authService.me,
        },
        {
          path: "about",
          element: <About />,
        },
      ],
    },
  ]);
};
