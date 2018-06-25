$(document).ready(function() {
    /**************
     Init Clipboard
     **************/
    new ClipboardJS('.omics-copy-btn');

    /**************
     iCommand Popup
     **************/
    $('.omics-irods-popup-cmd-btn').click(function () {
        var irodsPath = $(this).attr('irods-path');
        $('.modal-title').text('iRODS iCommands Access');

        var htmlData = '<div class="input-group">' +
            '<input id="omics-copy-field" class="form-control omics-code-input" type="text" value="icd ' + irodsPath + '" readonly/>' +
            '<div class="input-group-append">' +
            '<button class="btn btn-secondary omics-copy-btn" role="submit" data-clipboard-target="#omics-copy-field"><i class="fa fa-clipboard"></i> Copy</button></div>' +
            '</div>';

        $('.modal-body').html(htmlData);
    });
});
