const albums = {
  midnight: {
    title: "Midnight Echoes",
    type: "Nova Ray • New Single",
    cover: "images/album-1.png",
    audio: "music/cinematic-1.mp3",
    tracks: [
      ["01 • Midnight Echoes", "3:42"],
      ["02 • Electric Dreams", "4:11"],
      ["03 • Afterglow", "5:02"]
    ]
  },

  electric: {
    title: "Electric Dreams",
    type: "Nova Ray • Extended Play",
    cover: "images/album-2.png",
    audio: "music/cinematic-2.mp3",
    tracks: [
      ["01 • Electric Dreams", "4:11"],
      ["02 • Neon Skyline", "3:58"],
      ["03 • Night Drive", "4:26"]
    ]
  },

  afterglow: {
    title: "Afterglow",
    type: "Nova Ray • Full Album",
    cover: "images/album-3.png",
    audio: "music/cinematic-3.mp3",
    tracks: [
      ["01 • Afterglow", "5:02"],
      ["02 • City Lights", "3:49"],
      ["03 • Lost In Motion", "4:34"]
    ]
  }
};

const albumCards = document.querySelectorAll(".album-card");
const playerCover = document.querySelector(".player-cover img");
const playerTitle = document.querySelector(".player-info h3");
const playerType = document.querySelector(".player-info p");
const audioPlayer = document.querySelector(".audio-player");
const audioSource = document.querySelector(".audio-player source");
const trackList = document.querySelector(".track-list");

function loadAlbum(albumKey) {
  const album = albums[albumKey];

  playerCover.src = album.cover;
  playerCover.alt = `${album.title} Album Cover`;

  playerTitle.textContent = album.title;
  playerType.textContent = album.type;

  audioSource.src = album.audio;
  audioPlayer.load();

  trackList.innerHTML = "";

  album.tracks.forEach((track) => {
    const trackElement = document.createElement("div");
    trackElement.classList.add("track");

    trackElement.innerHTML = `
      <span>${track[0]}</span>
      <span>${track[1]}</span>
    `;

    trackElement.addEventListener("click", () => {
      audioSource.src = album.audio;
      audioPlayer.load();
      audioPlayer.play();
    });

    trackList.appendChild(trackElement);
  });

  albumCards.forEach(item => item.classList.remove("active-album"));

  document
    .querySelector(`[data-album="${albumKey}"]`)
    .classList.add("active-album");
}

albumCards.forEach(card => {
  card.addEventListener("click", () => {
    const albumKey = card.dataset.album;

    loadAlbum(albumKey);

    document.querySelector("#player").scrollIntoView({
      behavior: "smooth"
    });
  });
});

loadAlbum("midnight");

/* VIDEO POPUP PLAYER */

const videoModal = document.getElementById("videoModal");
const videoFrame = document.getElementById("videoFrame");
const closeVideo = document.querySelector(".close-video");
const videoThumbnails = document.querySelectorAll(".video-thumbnail");

const videoLinks = [
  "https://www.youtube.com/embed/ylj1lBUt7Ss",
  "https://www.youtube.com/embed/-fS9rORQtMI",
  "https://www.youtube.com/embed/1OAVoq37Dko"
];

videoThumbnails.forEach((thumbnail, index) => {
  thumbnail.addEventListener("click", () => {
    videoModal.classList.add("active");
    videoFrame.src = videoLinks[index] + "?autoplay=1";
  });
});

closeVideo.addEventListener("click", () => {
  videoModal.classList.remove("active");
  videoFrame.src = "";
});

videoModal.addEventListener("click", (e) => {
  if (e.target === videoModal) {
    videoModal.classList.remove("active");
    videoFrame.src = "";
  }
});

/* PARALLAX HERO */

window.addEventListener("scroll", () => {
  const hero = document.querySelector(".hero");
  const scrollPosition = window.scrollY;

  hero.style.backgroundPositionY = `${scrollPosition * 0.4}px`;
});