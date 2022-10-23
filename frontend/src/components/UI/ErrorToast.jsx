import React from 'react'
import { Alert, Toast, ToastContainer } from 'react-bootstrap'

const ErrorToast = ({error}) => {
  if (!error) {
    return <></>
  }
  console.log('info : error render : ', error)
  return (

    <Alert variant="warning" >
      <h5>{error.message}</h5>
      <p>{error.response?.data?.detail} {error.response?.data?.status}</p>
      <h5>see log in browser and in server terminal for more detail</h5>
    </Alert>

  )
}

export default ErrorToast