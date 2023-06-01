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
function sendRequest(url, redirect_url) {
    var checkboxes = document.querySelectorAll('.sodar-checkbox');
    var selectedRequests = [];

    checkboxes.forEach(function(checkbox) {
        if (checkbox.checked && checkbox.value !== 'on') {
            selectedRequests.push(checkbox.value);
        }
    });

    // Add params to URL
    var urlParams = url + selectedRequests[0] + '?irodsdatarequests=' + encodeURIComponent(selectedRequests.join(','));

    // Redirect to URL
    window.location.href = urlParams;
}
