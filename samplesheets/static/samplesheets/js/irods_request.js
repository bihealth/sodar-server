// JS for iRODS request page
$(document).ready(function () {
    // Disable "Accept Selected" and "Reject Selected" options by default
    $('#sodar-ss-accept-selected').addClass('disabled');
    $('#sodar-ss-reject-selected').addClass('disabled');

    // Enable "Accept Selected" and "Reject Selected" options if at least one
    // checkbox is checked or if the "Select All" checkbox is checked
    $('.sodar-ss-checkbox-item').change(function () {
        if ($('.sodar-ss-checkbox-item:checked').length > 0) {
            $('#sodar-ss-accept-selected').removeClass('disabled');
            $('#sodar-ss-reject-selected').removeClass('disabled');
        } else {
            $('#sodar-ss-accept-selected').addClass('disabled');
            $('#sodar-ss-reject-selected').addClass('disabled');
        }
        // Uncheck "Select All" if any checkbox is unchecked
        if ($('.sodar-ss-checkbox-item:checked').length < $('.sodar-ss-checkbox-item').length) {
            $('#sodar-ss-check-all').prop('checked', false);
        } else {
            $('#sodar-ss-check-all').prop('checked', true);
        }
    });
});

/*****************
 Manage checkboxes
 *****************/
function checkAll(elem) {
    // Enable if unchecked and disable if checked and show/hide buttons
    $('.sodar-ss-checkbox-item').each(function () {
        $(this).prop('checked', elem.checked);
        if (elem.checked) {
            $('#sodar-ss-accept-selected').removeClass('disabled');
            $('#sodar-ss-reject-selected').removeClass('disabled');
        }
        else {
            $('#sodar-ss-accept-selected').addClass('disabled');
            $('#sodar-ss-reject-selected').addClass('disabled');
        }
    });
}

/*****************
 * Accept or reject selected
 *****************/
function sendRequest(url) {
    var checkboxes = document.querySelectorAll('.sodar-checkbox');
    var selectedRequests = [];

    checkboxes.forEach(function(checkbox) {
        if (checkbox.checked && checkbox.value !== 'on') {
            selectedRequests.push(checkbox.value);
        }
    });

    // Create a form to send the POST request
    var form = document.createElement('form');
    form.setAttribute('method', 'post');
    form.setAttribute('action', url);

    // Create a CSRF token input field
    var csrfToken = jQuery("[name=csrfmiddlewaretoken]").val();
    var csrfField = document.createElement('input');
    csrfField.setAttribute('type', 'hidden');
    csrfField.setAttribute('name', 'csrfmiddlewaretoken');
    csrfField.setAttribute('value', csrfToken);
    form.appendChild(csrfField);

    // Add the data to the form
    var hiddenField = document.createElement('input');
    hiddenField.setAttribute('type', 'hidden');
    hiddenField.setAttribute('name', 'irodsdatarequests');
    hiddenField.setAttribute('value', selectedRequests.join(','));
    form.appendChild(hiddenField);
    document.body.appendChild(form);

    // Submit the form
    form.submit();
}
