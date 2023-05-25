// JS for iRODS request page
$(document).ready(function () {
    // Disable "Accept Selected" and "Reject Selected" options by default
    $('#sodar-ss-accept-selected').hide();
    $('#sodar-ss-reject-selected').hide();

    // Enable "Accept Selected" and "Reject Selected" options if at least one
    // checkbox is checked or if the "Select All" checkbox is checked
    $('.sodar-ss-checkbox-item').change(function () {
        if ($('.sodar-ss-checkbox-item:checked').length > 0) {
            $('#sodar-ss-accept-selected').show();
            $('#sodar-ss-reject-selected').show();
        } else {
            $('#sodar-ss-accept-selected').hide();
            $('#sodar-ss-reject-selected').hide();
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
            $('#sodar-ss-accept-selected').show();
            $('#sodar-ss-reject-selected').show();
        }
        else {
            $('#sodar-ss-accept-selected').hide();
            $('#sodar-ss-reject-selected').hide();
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
        if (checkbox.checked) {
            selectedRequests.push(checkbox.value);
        }
    });

    var data = {
        request_ids: selectedRequests
    };
    var csrftoken = getCookie('csrftoken');  // Retrieve the CSRF token from the cookie
    // console.log(csrftoken);
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken  // Include the CSRF token in the headers
        },
        body: JSON.stringify(data)
    })
    .then(function(response) {
        // Handle the response from the server
        // e.g., display a success message or perform further actions
    })
    .catch(function(error) {
        // Handle any errors that occurred during the request
        // e.g., display an error message or log the error
    });
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
