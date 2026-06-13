function testAlert() {
    Swal.fire({
        title: "Hello Raman!",
        text: "SweetAlert2 works!",
        icon: "success"
    });
}

function confirmDelete() {
    Swal.fire({
        title: "Delete post?",
        text: "You cannot undo this action.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Yes delete",
        cancelButtonText: "Cancel"
    }).then((result) => {

        if (result.isConfirmed) {
            Swal.fire({
                title: "Deleted!",
                text: "Your post has been deleted.",
                icon: "success"
            });
        }

    });
}
