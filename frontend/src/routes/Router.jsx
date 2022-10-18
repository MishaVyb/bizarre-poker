import { createBrowserRouter, Navigate } from 'react-router-dom'
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
import delay from '../utils/functools'

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
          action: async ({ params, request }) => {
            console.log('ACTION', params, request)
            // submiting a form (on <ControlPanel>) -> router `action` -> delay  -> reload `loader`
            // + post reqest to server API - need to make it before - so here is delay(..)
            await delay(100)
            // [todo]
            // await POST requst here !!
            // and only after that response loader will reload data from server
          },
          loader: gameService.gameDetailLoader, // one loader -> many requests

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
