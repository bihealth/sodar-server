$(document).ready(function() {
    /***************
     Init Clipboards
     ***************/
    new ClipboardJS('.omics-irods-copy-btn');

    /******************
     Copy link handling
     ******************/
    $('.omics-irods-copy-btn').click(function () {
        if ($(this).attr('data-table') !== '1') {
            var realTitle = $(this).tooltip().attr('data-original-title');
            $(this).attr('title', 'Copied!')
                .tooltip('_fixTitle')
                .tooltip('show')
                .attr('title', realTitle)
                .tooltip('_fixTitle');
        }
    });
});
