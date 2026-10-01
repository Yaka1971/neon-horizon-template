const data = window.NEON_DATA || {};
const albums = data.albums || {};

const albumCards = document.querySelectorAll(".album-card");
const playerCover = document.querySelector(".player-cover img");
const playerTitle = document.querySelector(".player-info h3");
const playerType = document.querySelector(".player-info p");
const audioPlayer = document.querySelector(".audio-player");
const audioSource = document.querySelector(".audio-player source");
const trackList = document.querySelector(".track-list");

function loadAlbum(albumKey) {
  const album = albums[albumKey];
  if (!album) return;

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

    const name = document.createElement("span");
    const duration = document.createElement("span");
    name.textContent = track[0];
    duration.textContent = track[1];
    trackElement.append(name, duration);

    trackElement.addEventListener("click", () => {
      audioSource.src = album.audio;
      audioPlayer.load();
      audioPlayer.play().catch(() => {});
    });
    trackList.appendChild(trackElement);
  });

  albumCards.forEach(item => item.classList.remove("active-album"));
  const selected = document.querySelector(`[data-album="${albumKey}"]`);
  if (selected) selected.classList.add("active-album");
}

albumCards.forEach(card => {
  card.addEventListener("click", () => {
    loadAlbum(card.dataset.album);
    document.querySelector("#player").scrollIntoView({ behavior: "smooth" });
  });
});

loadAlbum("midnight");

/* VIDEO POPUP PLAYER */
const videoModal = document.getElementById("videoModal");
const videoFrame = document.getElementById("videoFrame");
const closeVideo = document.querySelector(".close-video");
const videoThumbnails = document.querySelectorAll(".video-thumbnail");
const videoLinks = data.videos || [];

videoThumbnails.forEach((thumbnail, index) => {
  thumbnail.addEventListener("click", () => {
    if (!videoLinks[index]) return;
    videoModal.classList.add("active");
    videoFrame.src = videoLinks[index] + (videoLinks[index].includes("?") ? "&" : "?") + "autoplay=1";
  });
});

if (closeVideo) closeVideo.addEventListener("click", () => {
  videoModal.classList.remove("active");
  videoFrame.src = "";
});

if (videoModal) videoModal.addEventListener("click", (e) => {
  if (e.target === videoModal) {
    videoModal.classList.remove("active");
    videoFrame.src = "";
  }
});

/* PARALLAX HERO */
window.addEventListener("scroll", () => {
  const hero = document.querySelector(".hero");
  if (hero && window.innerWidth > 768) {
    hero.style.backgroundPositionY = `${window.scrollY * 0.4}px`;
  }
});
