// JQuery helpers for sheet version list

function checkAll(elem) {
  let checked = elem.checked
  $('.sodar-ss-version-check-item').each(function () {
    $(this).prop('checked', checked)
  })
}

$(document).ready(function () {
  // Handle enabling and disabling batch operations
  $('.sodar-ss-version-check').change(function () {
    let checkCount = 0
    $('.sodar-ss-version-check-item').each(function () {
      if ($(this).prop('checked') === true) checkCount++
    })
    // Update compare link
    if (checkCount === 2) {
      let sourceUuid = null
      let targetUuid = null
      let targetFound = false
      $('.sodar-ss-version-check-item').each(function () {
        if ($(this).prop('checked') === true) {
          if (!targetFound) {
            targetUuid = $(this).attr('value')
            targetFound = true
          } else sourceUuid = $(this).attr('value')
        }
      })
      let baseUrl = $('#sodar-ss-version-link-compare').attr(
        'data-base-url')
      let url = baseUrl + '?source=' + sourceUuid + '&target=' +
        targetUuid
      $('#sodar-ss-version-link-compare').attr('href', url).removeClass(
        'disabled')
    } else {
      $('#sodar-ss-version-link-compare').attr('href', '#').addClass(
        'disabled')
    }
    // Update delete link
    if (checkCount > 0) {
      $('#sodar-ss-version-link-delete').removeClass(
        'disabled').addClass('text-danger')
    } else {
      $('#sodar-ss-version-link-delete').addClass(
        'disabled').removeClass('text-danger')
    }
  })

  // Handle form submitting from remote link
  $('#sodar-ss-version-link-delete').click(function () {
    $('#sodar-ss-version-delete-form').submit()
  })
})
