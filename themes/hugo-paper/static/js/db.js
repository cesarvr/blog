(function(){
  const rnd = (limit) => Math.floor(Math.random() * limit) + 0
  const $phrase = $('.phrase')

  $.getJSON("db/db.json", function(result){
    let n = rnd(result.length)
    let phrase = result[n]
    $phrase.text(phrase.phrase)
    if(phrase.url !== '')
      $phrase.attr('href', phrase.url)
  })
})()
