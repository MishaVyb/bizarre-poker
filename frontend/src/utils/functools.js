

// call with 'avait' in async function
function delay(ms) {
  return new Promise((resolve, reject) => setTimeout(resolve, ms))
}

export default delay