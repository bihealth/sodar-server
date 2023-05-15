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
