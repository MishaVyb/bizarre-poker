
function importAll(r) {
  let images = {}
  r.keys().map((item, index) => { images[item.replace('./', '')] = r(item) })
  return images
}

export const cardImages = importAll(require.context('./cards', false, /\.(png|jpe?g|svg)$/))


