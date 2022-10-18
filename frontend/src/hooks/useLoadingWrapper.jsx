import { useState } from 'react'

function useLoadingWrapper(callback) {
  // принимает callback который вызывается асинхронно в новой асинхронной функции
  // это асинхронную функцию мы возвращаем первым аргументом
  // useLoadingWrapper оборачивает функцию async callback в обертку async wrapp
  // asyncFetching -- обертка
  // isLoading -- статус флаг -- изначально false и только после внешнего вызыова async wrapp - true

  const [isLoading, setIsLoading] = useState(false)
  //const [error, setError] = useState('');

  const wrapp = async (...args) => {
    setIsLoading(true)
    await callback(args) // дождемся...
    setIsLoading(false)
  }

  return [wrapp, isLoading]
}

export default useLoadingWrapper
