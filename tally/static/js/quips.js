/* Little things Tally says when you hover over (or tap) the big mascot on the home screen.
   Add more lines any time: one short, friendly sentence each, no em dashes. */
(function () {
  const T = (window.Tally = window.Tally || {});

  const QUIPS = [
    "I eat spreadsheets for breakfast.",
    "Feed me a CSV. I'm hungry.",
    "I promise not to judge your merged cells.",
    "My favorite number? All of them.",
    "I count things. It's kind of my whole personality.",
    "Psst. Try the sample coffee shop data.",
    "No data was harmed in the making of this report.",
    "Rows, columns... I love them all equally.",
    "I run on numbers and good vibes.",
    "Hi! I'm Tally. I'm better at math than small talk.",
    "Your data stays right here with me. Pinky promise.",
    "I check every pattern twice. Like Santa, but for statistics.",
    "Excel? CSV? I'm not picky.",
    "Fun fact: my hair is a tally mark. Count it!",
    "Boop! That tickles.",
    "Careful, I'm ticklish around the decimals.",
    "One spreadsheet a day keeps the confusion away.",
    "I'm small, but I've read millions of rows.",
    "Outliers are just numbers with big personalities.",
    "If your data could talk, I'd translate.",
    "I don't bite. Your spreadsheet might, though.",
    "Random noise? Not on my watch.",
    "Ready when you are!",
    "Zero coffee needed. I run on CSVs.",
    "I only show patterns that pass real tests. No guessing.",
    "I've got a good feeling about this one.",
    "Spreadsheets go in, stories come out.",
    "My hobbies include averaging and long walks through columns.",
    "Hello, human! Got numbers?",
    "Messy data? That's my favorite kind.",
    "I'll find the 'Total' rows so nothing gets counted twice.",
    "Somewhere in your file, a pattern is waiting to be found.",
    "I'm not saying I'm a genius. The statistics are saying it.",
    "Drag, drop, done. Well, I do the rest.",
    "Charts are just numbers wearing nice outfits.",
    "I speak fluent spreadsheet.",
    "Let's turn those cells into a story.",
    "Did someone say pivot table? I got chills.",
    "High five! Well, I don't have hands. High tally?",
    "Plot twist: your data is more interesting than you think.",
  ];

  // Extra lines while Tally is wearing a holiday costume.
  const SEASONAL = {
    pumpkin: ["Boo! Scary spreadsheet? I'll make it friendly.", "Trick or treat? I'll take a spreadsheet.", "I'm not orange because I'm scared of your data. Promise."],
    witch: ["Double, double, data trouble. I'll fix it.", "No spells needed. Just statistics.", "I turn messy data into stories. Basically magic."],
    pilgrim: ["I came over on the Spreadsheet Flower.", "Thankful for tidy columns."],
    turkey: ["Gobble gobble! Feed me data, not stuffing.", "I'm thankful for clean data.", "I'm stuffed... with numbers."],
    christmas: ["All I want for Christmas is a tidy CSV.", "I made a list and checked it twice. Statistically.", "Ho ho ho! Got any data for me?"],
    newyear: ["New year, new spreadsheets!", "My resolution: read more rows.", "Cheers to clean data this year!"],
    valentines: ["Will you be my data-ntine?", "Roses are red, charts can be blue, I found a pattern, just for you.", "I heart spreadsheets."],
    presidents: ["Four score and seven rows ago...", "I cannot tell a lie. Your data has a story."],
    stpatricks: ["Lucky you! I'm great at finding patterns.", "The real pot of gold? Clean data."],
    easter: ["I'm great at finding hidden eggs. And hidden trends.", "Some bunny wants to see your data!"],
    july4: ["Freedom from messy spreadsheets!", "Let's make some fireworks with your data."],
  };

  let last = "";

  function pick() {
    const costume = T.mascotPrefs && T.mascotPrefs.holidays && T.costumeFor ? T.costumeFor() : null;
    const seasonal = (costume && SEASONAL[costume]) || [];
    // seasonal lines show up often during the holiday, but not every time
    const pool = seasonal.length && Math.random() < 0.5 ? seasonal : QUIPS;
    let line = last;
    for (let tries = 0; line === last && tries < 10; tries++) line = pool[Math.floor(Math.random() * pool.length)];
    last = line;
    return line;
  }

  /* Wrap the home-screen mascot so it says something when hovered, focused or tapped. */
  T.wireQuips = function (wrap) {
    if (!wrap) return;
    const bubble = wrap.querySelector(".quip");
    const say = () => {
      bubble.textContent = pick();
      bubble.classList.remove("show");
      void bubble.offsetWidth; // restart the pop animation
      bubble.classList.add("show");
      const svg = wrap.querySelector(".mascot");
      if (svg && svg.classList.contains("mood-idle")) svg.outerHTML = T.mascot(84, "happy");
    };
    const hush = () => {
      bubble.classList.remove("show");
      const svg = wrap.querySelector(".mascot");
      if (svg && svg.classList.contains("mood-happy")) svg.outerHTML = T.mascot(84, "idle");
    };
    wrap.addEventListener("mouseenter", say);
    wrap.addEventListener("mouseleave", hush);
    wrap.addEventListener("focus", say);
    wrap.addEventListener("blur", hush);
    wrap.addEventListener("click", say); // tap on touch screens, or click for another line
  };

  T.quips = { all: QUIPS, seasonal: SEASONAL };
})();
