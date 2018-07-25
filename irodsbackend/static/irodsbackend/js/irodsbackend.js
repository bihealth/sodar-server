/***************************************
 Collection statistics updating function
 ***************************************/
var updateCollectionStats = function() {
    $('span.omics-irods-stats').each(function () {
        var statsSpan = $(this);

        $.ajax({
            url: $(this).attr('stats-url'),
            method: 'GET',
            dataType: 'json'
        }).done(function (data) {
            var fileSuffix = 's';

            if (data['file_count'] === 1) {
                fileSuffix = '';
            }

            statsSpan.text(
                data['file_count'] + ' data file' + fileSuffix +
                ' ('+ humanFileSize(data['total_size'], true) + ')');
        }).fail(function (response) {
            statsSpan.text('Stats unavailable');
        });
    });
};

$(document).ready(function() {
    /***********************
     Update collection stats
     ***********************/
    updateCollectionStats();
    var statsInterval = 8 * 1000;  // TODO: Get setting from Django

    // Poll and update active zones
    setInterval(function () {
        updateCollectionStats();
    }, statsInterval);
});
