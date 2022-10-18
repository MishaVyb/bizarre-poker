import React, { useContext, useEffect } from 'react'
import { AuthContext } from '../context'
import Login from './Login'

const Logout = () => {
  const { auth, setAuth } = useContext(AuthContext)

  // exicuting function
  const logout = async () => {
    if (auth) {
      console.log('logout, remove this auth: ' + { ...auth })
      localStorage.removeItem('username')
      localStorage.removeItem('token')
      setAuth(null)
    } else {
      console.log('logging out when no auth provided')
    }
  }

  // trigger on component mount
  useEffect(() => {
    logout()
  })

  return (
    <div>
      <h4>
        see ya! <small className="text-muted">coming back soon</small>
      </h4>
      <Login preventCamingBack={true}/>
    </div>
  )
}

export default Logout
