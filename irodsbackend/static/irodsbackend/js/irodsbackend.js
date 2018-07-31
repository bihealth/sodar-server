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
        });
    });
};

$(document).ready(function() {
    /***************
     Init Clipboards
     ***************/
    new ClipboardJS('.omics-irods-copy-btn');

    /******************
     Copy link handling
     ******************/
    $('.omics-irods-copy-btn').click(function () {
        $(this).addClass('text-warning');

        if ($(this).attr('data-table') !== '1') {
            var realTitle = $(this).tooltip().attr('data-original-title');
            $(this).attr('title', 'Copied!')
                .tooltip('_fixTitle')
                .tooltip('show')
                .attr('title', realTitle)
                .tooltip('_fixTitle');
        }

        $(this).delay(250).queue(function() {
            $(this).removeClass('text-warning').dequeue();
        });
    });

    /***********************
     Update collection stats
     ***********************/
    updateCollectionStats();
    var statsInterval = 8 * 1000;  // TODO: Get setting from Django

    // Poll and update active collections
    setInterval(function () {
        updateCollectionStats();
    }, statsInterval);

    /***************
     Link list Popup
     ***************/
    $('.omics-irods-popup-list-btn').click(function() {
        var listUrl = $(this).attr('list-url');
        var irodsPath = $(this).attr('irods-path');
        var irodsPathLength = irodsPath.split('/').length;
        var webDavUrl = $(this).attr('webdav-url');
        var htmlData = '';
        var showChecksumCol = false;

        if (typeof(window.irodsShowChecksumCol) !== 'undefined') {
            showChecksumCol = window.irodsShowChecksumCol;
        }

        $('.modal-title').text('Files in iRODS: ' + irodsPath.split('/').pop());

        $.ajax({
                url: listUrl,
                method: 'GET',
                dataType: 'json'
            }).done(function (data) {
            // console.log(data);  // DEBUG

            if (data['data_objects'].length > 0) {
                htmlData += '<table class="table omics-card-table table-striped omics-irods-obj-table">';
                htmlData += '<thead><th>File</th><th>Size</th><th>Modified</th>';

                if (showChecksumCol === true) {
                    htmlData += '<th>MD5</th>';
                }

                htmlData += '</thead><tbody>';

                $.each(data['data_objects'], function (i, obj) {
                    var objNameSplit = obj['path'].split('/');
                    var objLink = '<a href="' + webDavUrl + obj['path'] + '"><span class="text-muted">';
                    objLink += objNameSplit.slice(irodsPathLength, objNameSplit.length - 1).join('/');
                    objLink += '/</span>' + obj['name'] + '</a>';
                    htmlData += '<tr><td>' + objLink + '</td>';
                    htmlData += '<td>' + humanFileSize(obj['size'], true) + '</td>';
                    htmlData += '<td>' + obj['modify_time'] + '</td>';
                    htmlData += '<td>';

                    if (showChecksumCol === true) {
                        if (obj['md5_file'] === true) {
                            htmlData += '<span class="text-muted"><i class="fa fa-check"></i></span>';
                        }

                        else {
                            htmlData += '<span class="text-danger"><i class="fa fa-close"></i></span>';
                        }
                    }

                    htmlData += '</td></tr>';
                });
            }

            else {
                htmlData += popupNoFilesHtml;
            }

            // Set success content and toggle modal
            $('.modal-body').html(htmlData);
            $('#omics-modal-wait').modal('hide');
            $('#omics-modal').modal('show');
        }).fail(function (response) {
            // Set failure content and toggle modal
            if (response.status === 404) {
                $('.modal-body').html(
                    '<span class="text-muted font-italic">Collection not found</span>');
            }

            else {
                $('.modal-body').html(
                    '<span class="text-danger font-italic">Failed to query data (' +
                    response.status + ': ' + response.responseText + ')</span>');
            }

            $('#omics-modal-wait').modal('hide');
            $('#omics-modal').modal('show');
        });

        // Set waiting content and toggle modal
        $('#omics-modal-wait').modal('show');
    });
});
