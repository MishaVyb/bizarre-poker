import React from 'react'
import { useLoaderData } from 'react-router-dom'

const MePage = () => {
  const userDetail = useLoaderData()
  console.log('GameListPage' + {...userDetail})
  return (
    <div>
      {userDetail.id} | {userDetail.username}
    </div>
  )
}

export default MePage