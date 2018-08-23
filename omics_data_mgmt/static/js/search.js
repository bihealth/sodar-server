// Set up DataTables for search tables
$(document).ready(function() {
    $.fn.dataTable.ext.classes.sPageButton =
        'btn btn-secondary omics-list-btn ml-1 omics-paginate-button';

    $('.omics-search-table').each(function() {
        $(this).DataTable({
            scrollX: false,
            paging: true,
            pageLength: window.searchPagination,
            scrollCollapse: true,
            info: false,
            language: {
                paginate: {
                    previous: '<i class="fa fa-arrow-circle-left"></i> Previous',
                    next: '<i class="fa fa-arrow-circle-right"></i> Next'
                }
            },
            dom: 'tp'
        });

        // Hide pagination if only one page
        console.log('pages=' + $(this).DataTable().page.info().pages);
        if ($(this).DataTable().page.info().pages === 1) {
            $(this).next('.dataTables_paginate').hide();
        }

        $(this).closest('div.omics-search-card').show();
    });

    $('div#omics-search-not-found-alert').removeClass('d-none');

    // Update overflow status
    modifyCellOverflow();
});