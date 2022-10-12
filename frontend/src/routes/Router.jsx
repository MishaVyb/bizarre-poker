import { createBrowserRouter, Navigate, useNavigate } from 'react-router-dom'
import React from 'react'

import Root from './Root'
import GamePage from './GameDetailPage'
import About from './About'
import ErrorPage from './ErrorPage'
import GameListPage from './GamesPage'
import Login from './Login'
import { useContext } from 'react'
import { AuthContext } from '../context'
import Logout from './Logout'
import MePage from './MePage'

const AuthRequired = ({ children }) => {
  const { auth } = useContext(AuthContext)
  if (!auth) {
    console.log('->auth-required-redirection->')
    return (
      <Navigate to="/login" /*state={{prevented: children}}*/ replace />
    )
  }
  return children
}

const AnonymousOnly = ({ children }) => {
  const { auth } = useContext(AuthContext)
  if (auth && !auth.isLoading) {
    console.log('->anonimous-only-redirection->')
    return <Navigate to="/me" replace />
  }
  return children
}

// export const getRouter_fake = (authService, gameService) => {
//   return createBrowserRouter([
//     {
//       path: "/",
//       element: <Root />,
//       errorElement: <ErrorPage />,
//       children: [

//       ],
//     },
//   ]);
// };

export const getRouter = (authService, gameService) => {
  // make sure that all methods for services are bounded (!)
  return createBrowserRouter([
    {
      path: '/',
      element: (<Root />),
      errorElement: <ErrorPage />,
      children: [
        {
          path: '/',
          element: <GameListPage />,
          loader: gameService.getAll,
        },
        {
          path: 'games/:gameId',
          element: (
            <AuthRequired>
              <GamePage />
            </AuthRequired>
          ),
          loader: gameService.gameDetailLoader,
        },
        {
          path: 'login',
          element: (
            <AnonymousOnly>
              <Login />
            </AnonymousOnly>
          ),
        },
        {
          path: 'logout',
          element: (
            //<AuthRequired>
            <Logout />
            //</AuthRequired>
          ),
        },
        {
          path: 'me',
          element: (
            <AuthRequired>
              <MePage />
            </AuthRequired>
          ),
          loader: authService.me,
        },
        {
          path: 'about',
          element: <About />,
        },
      ],
    },
  ])
}
