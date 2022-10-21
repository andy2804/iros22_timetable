// parser
papers = Array.from(document.querySelectorAll("span.pTtl > a")).map(el => ({
  date: document.querySelector("h3").innerText.replace("Technical Program for ", ""),
  time: el.parentElement.parentElement.parentElement.previousElementSibling.querySelector("a").innerText.split(", ")[0],
  id: el.parentElement.parentElement.parentElement.previousElementSibling.querySelector("a").innerText.split(", ")[1],
  abstract: document.querySelector("#Ab"+el.onclick.toString().match(/[0-9]+/)[0]).innerText.split("\n").map(line => line.trim()).join("\n").trim(),
  title: el.innerText.split("\n")[0],
}));
rooms = Object.fromEntries(Array.from(document.querySelectorAll(".sHdr")).filter(el => !el.previousElementSibling || !el.previousElementSibling.classList.contains("sHdr")).map(el => el.innerText.split("\t")));
document.write(`papers.json<br><textarea>${JSON.stringify(papers, null, 2)}</textarea><br>rooms.json<br><textarea>${JSON.stringify(rooms, null, 2)}</textarea>`);

