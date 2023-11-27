if (document.location.protocol != "https:") {
	//document.location.protocol = "https:";
}

var ctxpath = document.location.pathname.substring(0,document.location.pathname.lastIndexOf('/'));
var fileSep = null;
var ajax = null;
var socket = null;
var fileObj = null;
var targetPath = document.getElementById("target-path");
var fileName = document.getElementById("file-name");
var fileName2 = document.getElementById("file-name2");
var statusLog = document.getElementById("status-log");
var btnConnect = document.getElementById("btn-connect");
var btnReload = document.getElementById("btn-reload");
var btnUpload = document.getElementById("btn-upload");
var btnActionOK = document.getElementById("btn-action-ok");
var btnDownload = document.getElementById("btn-download");
var btnDelete = document.getElementById("btn-delete");
var btnChangeDir = document.getElementById("btn-chdir");
var cbOverwrite = document.getElementById("cb-overwrite");
var btnClear = document.getElementById("btn-clear");
var btnLink = document.getElementById("btn-link");
var progressBar = document.getElementById("progress-bar");
var btnCancelUpload = document.getElementById("btn-cancel-upload");
var fileTable = null;
var totalSentBytes = 0;
var closeSocketClicked = false;
var oldPath = targetPath.value;

var logging_info = function(message) {
	statusLog.innerHTML += message + "<br/>";
	statusLog.scrollTop = statusLog.scrollHeight;
};

var logging_warn = function(message) {
	statusLog.innerHTML += "<font color='red'>" + message + "</font><br/>";
	statusLog.scrollTop = statusLog.scrollHeight;
};

var browser = (function() {
	var s = navigator.userAgent.toLowerCase();
	var match = /(webkit)[ \/](\w.]+)/.exec(s) ||
				/(opera)(?:.*version)?[ \/](\w.]+)/.exec(s) ||
				/(msie) ([\w.]+)/.exec(s) ||
				!/compatible/.test(s) && /(mozilla)(?:.*? rv:([\w.]+))?/.exec(s) ||
				[];
	return { name: match[1] || "", version: match[2] || "0" };
}());

function endsWith(str, ch) {
    return (str.lastIndexOf(ch) == str.length-1)
}

function joinPath(first, second) {
    if (endsWith(first, fileSep)) {
        return first + second;
    } else {
        return first + fileSep + second;
    }
}

function redrawTable() {
	if (fileTable != null) {
		fileTable.clear().draw();
		btnReload.disabled = true;
	}
	var path_to_list = targetPath.value.trim();
	if (path_to_list == "") {
    	socket.send("--@init");
	} else {
		socket.send("--@list:"+path_to_list);
	}
}

function setFile(srcObj, f) {
	if (f == null) {
		if (browser.name == "msie") {
			$(fileName2).replaceWith($(fileName2).clone(true));
		} else { 
			$(fileName2).val("");
		}
		fileObj = null;
		fileName.value = "";
		btnUpload.disabled = true;
	} else {
        logging_info("Selected a file to upload: size=" + f.size);
	    fileObj = f;
		fileName.value = f.name;
		btnUpload.disabled = false;
	}
}

function uploadChunk(start) {
	var BYTES_PER_CHUNK = 1024 * 1024;
	var end = start + BYTES_PER_CHUNK;
	var fileSize = fileObj.size;
	if (start >= fileSize) {
        logging_info("Sent the file completely.");
		socket.send("--@upload:#end#");
		progressBar.classList.remove("progress-bar-animated");
	 	totalSentBytes = 0;
		setFile(null, null);
	} else {
		fileReader = new FileReader();
	   	fileReader.onload = function(e) {
   			rawData = e.target.result;
	        socket.send(rawData);
		}
		var chunkFile = fileObj.slice(start, end);
		fileReader.readAsArrayBuffer(chunkFile);
	}
}

function requestDownload(path_to_download) {
	$.ajax({
		type: "POST",
		url: ctxpath + "/ws/token",
		cache: false,
		dataType: "JSON",
		data: { "filepath":path_to_download },
        success: function(result){
            downloadFile(result["filepath"],  result["token"]);
        },
        error : function(request, status, error) {
            alert("Failed to get token : " + error);
        }
    });
}

function downloadFile(path_to_download, token_for_downlaod) {
	$.ajax({
		type: "POST",
		url: ctxpath + "/ws/download",
		cache: false,
		data: { "filepath":path_to_download, "token": token_for_downlaod },
        xhrFields: {
            responseType: 'blob' // to avoid binary data being mangled on charset conversion
        },
		success: function (data, message, xhr) {
			if(xhr.readyState == 4 && xhr.status == 200) {
				let disposition = xhr.getResponseHeader('Content-Disposition');
				let filename;
				if (disposition && disposition.indexOf('attachment') !== -1) {
					let filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
					let matches = filenameRegex.exec(disposition);
					if (matches != null && matches[1]) filename = matches[1].replace(/['"]/g, '');
				}
				let blob = new Blob([data]);
				let link = document.createElement('a');
				link.href = window.URL.createObjectURL(blob);
				link.download = decodeURIComponent(filename);
				link.click();
			}else{
				alert("Failed to download : response_code=" + xhr.status);
			}
		},
        error : function(request, status, error) {
            alert("Failed to download : " + error);
        }
    });
}

function connectToServer() {
	if (socket == null) {
        if (document.location.protocol == "https:") {
            socket = new WebSocket("wss://" + document.location.host + ctxpath + "/ws/file");
		} else {
            socket = new WebSocket("ws://" + document.location.host + ctxpath + "/ws/file");
		}
		socket.addEventListener("open", function() {
			logging_info("Connected to server.");
			btnDownload.disabled = false;
			btnDelete.disabled = false;
			btnReload.disabled = false;
			btnUpload.disabled = (fileObj == null);
			btnChangeDir.disabled = false;
			btnConnect.innerHTML = "Disconnect";
			btnConnect.classList.add("btn-danger");
			btnConnect.classList.remove("btn-success");
			redrawTable();
			console.log("connection open");
		});
	    socket.addEventListener("close", function() {
			logging_warn("Closed the socket.");
			btnDownload.disabled = true;
			btnDelete.disabled = true;
			btnReload.disabled = true;
			btnUpload.disabled = true;
			btnChangeDir.disabled = true;
			btnConnect.innerHTML = "Connect";
			btnConnect.classList.add("btn-success");
			btnConnect.classList.remove("btn-danger");
			socket = null;
	        console.log("connection close");
			if (closeSocketClicked == false) {
				setTimeout(connectToServer, 10000);
			}
	    });
	    socket.addEventListener("error", function(e) {
			logging_warn("Error received from socket: " + e.msg);
	        console.log("Error : " + e.msg);
	    });
		socket.addEventListener("message", function(msg) {
			logging_info(msg.data);
			onMessage(msg);
		});
		closeSocketClicked = false;
	} else {
		closeSocketClicked = true;
		socket.close();
	}
}

function onMessage(msg) {
	var idx = msg.data.indexOf(":") + 1;
	var state = msg.data.substring(idx, msg.data.indexOf(":",idx));
	var detail = msg.data.substring(msg.data.indexOf(":",idx)+1);
	if (state == "#error#") {
		logging_warn("Error occurred: " + detail);
		alert("Error occurred: " + detail);
		return;
	}
	if (msg.data.substring(0, 8) == "--@init:")  {
	    if (state == "#dir#") {
	        fileSep = detail.indexOf("\\") > 0 ? "\\" : "/"
			targetPath.value = detail;
			redrawTable();
		}
	} else	if (msg.data.substring(0, 10) == "--@upload:")  {
		if (state == "#ready#") {
       		logging_info("Ready to upload: path=" + detail);
			totalSentBytes = 0;
			$('#progress-modal').modal('show');
			uploadChunk(0);
		} else if (state == "#continue#") {
       		logging_info("Sent the chunk of file: size=" + detail);
			var sent_bytes = Number(detail);
			totalSentBytes += sent_bytes;
			var progress_pct = Math.round(totalSentBytes/fileObj.size*100) + "%";
			progressBar.style.width = progress_pct;
			progressBar.textContent = progress_pct;
			uploadChunk(totalSentBytes);
		} else if (state == "#cancel#") {
			logging_warn("Canceled uploading the file: size=" + detail + "/" + fileObj.size);
			alert("Upload canceled.");
			redrawTable();
		} else if (state == "#finish#") {
			logging_info("Upload successed: size=" + detail);
			setTimeout(function() {
				$('#progress-modal').modal('hide');
				alert("Upload successed.");
				redrawTable();
			}, 500);
		}
	} else if (msg.data.substring(0, 10) == "--@delete:")  {
		if (state == "#finish#") {
       		logging_info("Delete successed: path=" + detail);
	        alert("Delete successed.");
			redrawTable();
		} else if (state == "#deny#") {
       		logging_warn("Perission denied: path=" + detail);
		} else if (state == "#directory#") {
       		logging_warn("Directory does not allow to delete: path=" + detail);
		} else if (state == "#not_exists#") {
       		logging_warn("Not exists: path=" + detail);
		}
	} else if (msg.data.substring(0, 8) == "--@list:")  {
		if (state == "#finish#") {
			var file_list = JSON.parse(Base64.decode(detail));
			fileTable.search("");
			fileTable.order([]);
			fileTable.clear();
			for (var i = 0; i < file_list.length; i++) {
				if (file_list[i].name == '.')
					continue;
				fileTable.row.add([
					file_list[i].name,
					file_list[i].type=="D"?"Dir":(file_list[i].type=="L"?"Link":(file_list[i].type=="F"?"File":"Unknown")),
					file_list[i].user,
					file_list[i].group,
					file_list[i].perm,
					moment.unix(file_list[i].mtime).format("YYYY-MM-DD HH:mm:ss"),
					$.number(file_list[i].size),
					file_list[i].link
				]);
			}
			fileTable.draw();
			$("#file-table tr.link td:nth-child(2)").each(function() {
				var link_name = fileTable.row($(this).parents("tr")).data()[7];
				$(this).tooltip({title: link_name});
			});
			btnReload.disabled = false;
			oldPath = targetPath.value;
       		logging_info("Refresh file list: count=" + file_list.length);
		} else if (state == "#dir#") {
			targetPath.value = detail;
		} else {
			if (state == "#deny#") {
       			logging_warn("Perission denied: path=" + detail);
			} else if (state == "#file#") {
       			logging_warn("File does not allow to list: path=" + detail);
			} else if (state == "#not_exists#") {
       			logging_warn("Not exists: path=" + detail);
			}
	        alert("Cannot go to '" + detail + "' : " + state.substring(1,state.length-1) + "\nBack to '" + oldPath + "'");
			targetPath.value = oldPath;
			redrawTable();
		}
	}
}


$(document).ready(function() {
    fileTable = $('#file-table').DataTable({
		"createdRow": function (row, data, index) {
			if (data[1] == "Dir") {
				$(row).addClass('dir');
			} else if (data[1] == "Link") {
				$(row).addClass('link');
			}
		},
        "scrollX": true,
        "scrollY": "40vh",
        "scrollCollapse": true,
        "autoWidth": false,
        "paging": false,
        "order": [],
		"columnDefs": [ 
			{ "targets": 1, "width": "60px" },
			{ "targets": 2, "width": "80px" },
			{ "targets": 3, "width": "80px" },
			{ "targets": 4, "width": "100px" },
			{ "targets": 5, "width": "140px" },
			{ "targets": 6, "width": "70px" },
            {
				"title": "Link",
                "targets": [7],
                "visible": false,
                "searchable": false
            }
        ]
    });
    $('#file-table tbody').on('click', 'tr', function() {
		if (fileTable.row(this).data()[1] == "Dir") {
			$('#dirModalLabel')[0].textContent = joinPath(targetPath.value, fileTable.row(this).data()[0]);
			$('#dir-modal').modal('show');
		} else if (fileTable.row(this).data()[1] == "Link") {
			$('#btn-link').show();
			$('#fileModalLabel')[0].textContent = fileTable.row(this).data()[0];
			$('#fileModalLink')[0].textContent = fileTable.row(this).data()[7];
			$('#file-modal').modal('show');
		} else {
			$('#btn-link').hide();
			$('#fileModalLabel')[0].textContent = fileTable.row(this).data()[0];
			$('#file-modal').modal('show');
		}
    });
	$('#file-name').tooltip();
	connectToServer();
});


btnClear.addEventListener("click", function() {
	statusLog.innerHTML = "";
});

targetPath.addEventListener("change", function(e) {
	var fixedPath = e.target.value.trim();
	if (fileSep == "/") {
        if (fixedPath.indexOf("/") < 0) {
            fixedPath = "/" + fixedPath;
        }
        while (fixedPath.length > 1 && endsWith(fixedPath, "/")) {
            fixedPath = fixedPath.substring(0, fixedPath.length-1);
        }
	} else {
	    if (endsWith(fixedPath, ":")) {
            fixedPath = fixedPath + "\\";
	    }
	}
    targetPath.value = fixedPath;
	redrawTable();
});

targetPath.addEventListener("keyup", function(e) {
    if (e.keyCode == 13) {
		this.blur();
    }
});

fileName.addEventListener("dragenter", function(e) {
	e.preventDefault();
	e.target.classList.add("active");
});

fileName.addEventListener("dragleave", function(e) {
	e.preventDefault();
	e.target.classList.remove("active");
})

fileName.addEventListener("dragover", function(e) {
	e.preventDefault();
});

fileName.addEventListener("click", function(e) {
	e.preventDefault();
	$(fileName2).trigger('click');
});

fileName.addEventListener("drop", function(e) {
	e.preventDefault();
	e.target.classList.remove("active");
	if (e.dataTransfer.files.length == 1) {
		setFile(this, e.dataTransfer.files[0]);
	} else {
        logging_warn("Error: only one file allow to upload");
		setFile(null, null);
    }
});

fileName2.addEventListener("change", function(e) {
	e.preventDefault();
	setFile(this, e.target.files[0]);
});

btnConnect.addEventListener("click", function() {
	connectToServer();
});

btnReload.addEventListener("click", function() {
	redrawTable();
});

btnUpload.addEventListener("click", function() {
	$('#btn-action-ok')[0].textContent = "Upload";
	$('#confirm-modal').modal('show');
});

btnDelete.addEventListener("click", function() {
	$('#btn-action-ok')[0].textContent = "Delete";
	$('#confirm-modal').modal('show');
});

btnActionOK.addEventListener("click", function() {
	var action = $('#btn-action-ok')[0].textContent;
    if (action == "Upload") {
	    if (fileObj == null) {
			alert("No file selected.");
	    } else {
			progressBar.style.width = "0%";
			progressBar.textContent = "0%";
			progressBar.classList.add("progress-bar-animated");
			if (cbOverwrite.checked) {
		    	socket.send("--@upload:#begin.ow#:"+joinPath(targetPath.value,fileObj.name));
			} else {
		    	socket.send("--@upload:#begin#:"+joinPath(targetPath.value,fileObj.name));
			}
	    }
	} else if (action == "Delete") {
		var path_to_delete = joinPath(targetPath.value, $('#fileModalLabel')[0].textContent);
		socket.send("--@delete:"+path_to_delete);
	}
});

btnDownload.addEventListener("click", function() {
	var path_to_download = joinPath(targetPath.value, $('#fileModalLabel')[0].textContent);
	logging_info("Downloading the file: path=" + path_to_download);
    requestDownload(path_to_download);
});

btnChangeDir.addEventListener("click", function() {
	targetPath.value = $('#dirModalLabel')[0].textContent;
	redrawTable();
});

btnLink.addEventListener("click", function() {
	var file_link = $('#fileModalLink')[0].textContent;
	targetPath.value = file_link.substring(0, file_link.lastIndexOf(fileSep));
	redrawTable();
});

btnCancelUpload.addEventListener("click", function() {
	logging_info("Requested to cancel uploading.");
	socket.send("--@upload:#cancel#");
});
