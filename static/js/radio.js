// code for play songs
var baseurl = "http://127.0.0.1:8888";
var wavesurfer = null;

var getOnlyNextSong = false;
var categoryId = 1;

var playingSong = null;
var nextSong = null;

var startTime = 0;


$(document).ready(function(){
	initializeRadio();
});


function set_var(channelid){
	categoryId = parseInt(channelid);
}

function initializeRadio(){
	wavesurfer = WaveSurfer.create({
		container: '#waveform',
		waveColor: 'grey',
		progressColor: 'purple',
		scrollParent: true,
		splitChannels: false,
		height: 160,
		interact:false
	});


	getSong(function(err, songs){
		if(err){
			alert(err);
		}else{
			console.log(songs);
			playingSong = songs.playing;

			nextSong = songs.next;

			startTime = playingSong.length - playingSong.remaining;
			playSong(playingSong);
		}
	});
}

function playSong(song){
	wavesurfer.load(song.file_path);
	
	document.getElementById("ps-name").innerHTML = song.name;
	document.getElementById("ps-added-by").innerHTML = "<i>-added by</i> "+song.added_by;
	if(song.thumbnail){
		document.getElementById("ps-thumbnail").innerHTML = '<img src="'+song.thumbnail+'">';
	}
	
	wavesurfer.on('ready', function () {
		if(startTime){
			console.log("seeeek---"+startTime);
			wavesurfer.play(startTime);
			startTime = 0;
		}else{
			wavesurfer.play(0);
		}
	});
	
	wavesurfer.on('finish', function () {
		playNextSong();
	});
}

function playNextSong(){
	playingSong = nextSong;
	playSong(playingSong);
	getSong(function(err, song){
		if(!err){
			nextSong = song.next;
		}
	});
}

function getSong(callback){
	var playlistType;
	
	if(getOnlyNextSong) playlistType = "next";
	else{
		playlistType = "fresh";
		getOnlyNextSong = true;
	}
	var url =baseurl+"/radio/playlist?type="+playlistType+"&cat="+categoryId;
	$.ajax({
		url:url,
		type:"GET",
		crossDomain: true,
		dataType: "json",
		contentType: "application/json; charset=utf-8",
		cache: false,
		success: function(data){
			callback(null, data);
		},
		error: function(XMLHttpRequest, textStatus, errorThrown){
			callback('ERROR! Please refresh');
			// console.log(textStatus);
			// console.log(XMLHttpRequest);
			// alert("Status: " + textStatus);
			// alert("Error: " + errorThrown);
		}
	});
}




// code for upvote and downvote songs
function poll_action(e, action){
	var action_class = "glyphicon-thumbs-down";
	if(action=="upvote"){
		action_class = "glyphicon-thumbs-up";
	}
	$(e).removeClass(action_class);
	$(e).addClass("glyphicon-refresh glyphicon-refresh-animate");
	
	var songid = e.getAttribute("songid");
	var token = e.getAttribute("token");
	alert(token);
	var upbote_points=10;
	// var cs = document.defaultView.getComputedStyle(e,null);
	// var color = cs.getPropertyValue('color');
	// alert(color);
	var url =baseurl+"/radio/playlist/polling?type="+action+"&songid="+songid+"&token="+token+"&count="+upbote_points;
	$.ajax({
		url:url,
		type:"GET",
		dataType: "json",
		crossDomain: true,
		contentType: "application/json; charset=utf-8",
		cache: false,
		success: function(data){
			//callback(null, data);
			$(e).removeClass("glyphicon-refresh glyphicon-refresh-animate");
			$(e).addClass(action_class);
			if (data.success){
				$(e).addClass("ld-active");
			}else{
				alert(data.error);
			}
		},
		error: function(XMLHttpRequest, textStatus, errorThrown){
			//callback('ERROR! Please refresh');
			console.log(textStatus);
			console.log(XMLHttpRequest);
			// alert("Status: " + textStatus);
			// alert("Error: " + errorThrown);
		}
	});
}