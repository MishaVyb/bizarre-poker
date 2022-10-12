import './../node_modules/bootswatch/dist/sketchy/bootstrap.css'
import React from 'react'

import { AuthContext } from './context'
import { useEffect, useMemo, useState } from 'react'
import { getRouter } from './routes/Router'
import { RouterProvider } from 'react-router-dom'
import AuthService from './services/AuthService'
import GameService from './services/GameService'

function App() {

  // global auth state // setAuth will make changes to services and router also
  const [auth, setAuth] = useState({isLoading: true})

  // memo 1 -- services
  const services = useMemo(() => {
    return {
      authService: new AuthService(auth?.token),
      gameService: new GameService(auth?.token),
    }
  }, [auth])

  // memo 2 -- router
  const router = useMemo(() => {return getRouter(services.authService, services.gameService)
  }, [services])

  // on mount -- load auth from local storage
  // it will make effect on memo-1 and memo-2
  useEffect(() => {
    if (localStorage.getItem('token')) {
      const loadedAuth = {
        username: localStorage.getItem('username'),
        token: localStorage['token'],
      }
      setAuth(loadedAuth)
    } else {
      setAuth(null)
    }
  }, []) // no dependencis, only at first compinen mount

  // const setAuthChangeRoutes = (auth) => {
  //   setAuth(auth);
  // };

  console.log(
    'APP RUNNING WITH: ',
    { ...auth },
    { ...services },
  )
  return (
    <div className="App">
      <AuthContext.Provider
        value={{ auth, setAuth, ...services}}
      >
        <RouterProvider router={router} />
      </AuthContext.Provider>
    </div>
  )
}

export default App
