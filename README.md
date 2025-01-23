<h1 align='center'>SARA v1.0</h1>

## About SARA

**SARA** *(Security Assistant Researcher Analyzer)* is an **asynchronous web crawler with enumeration capabilities**.
<p>The primary goal of the tool is to crawl target addresses, analyze source code and JavaScript files, and search for keywords, comments, and inline scripts. It also supports custom headers for flexibility.</p>
<p>Also there is an animation indicating that the program is running is included. The message <code>I’m running</code> will add a <code>.</code> every second to show activity.</p>

<h3><ins>Key Features:</ins></h3>
    <ul>
        <li><b>Crawling and Analysis:</b> SARA scans pages, extracting valuable information such as links, JavaScript files, and analyzing their content.</li>
        <li><b>Directory and Subdomain Enumeration:</b> Perfect for discovering niche endpoints like <code>/api</code> or <code>/graphql</code>, as well as enumerating subdomains.</li>
        <li>Simulated User Behavior:</li>
            <ul>
                <li>The <code>User-Agent</code> header is randomly chosen from a preset list to mimic real browsers (e.g., Chrome, Firefox) and OS (e.g., Macintosh, Linux, Windows)</li>
                <li>Users can specify their own <code>User-Agent</code>, overriding the default one.</li>
                <li>The tool introduces a delay between requests (1–5 seconds) to simulate natural user behavior, minimizing noise and suspicion.</li>
            </ul>
    </ul>

<h3><ins>Ideal For:</ins></h3>
    <ul>
        <li>Conducting penetration tests.</li>
        <li>Bug bounty programs that require deep automation with minimal detection and noise.</li>
    </ul>

### Example Output
Here is an example of the `--help` command output:

![SARA Help Command Output](https://github.com/Kode-n-Rolla/sara/blob/main/images/sara_help_flag.jpg)

<details><summary><h2><ins>Detailed Description</ins></h2></summary>
    <b>SARA</b> provides extensive functionality through its flags and modes. Below is a detailed description of each:
    <ol>
        <li><code>-t</code></li>
            <p>Accepts a single URL, a domain, or a file containing multiple targets. Works in conjunction with the three primary modes: <code>-c</code>, <code>--enum-s</code>, and <code>--enum-d</code>.</p>
        <li><code>-c</code> (<b>Crawling Mode</b>). Accepts either a single URL or a file containing multiple URLs.</li>
            <p>In crawling mode, SARA gathers key data about the target, including:</p>
                <ul>
                    <li>HTTP response codes</li>
                    <li>Links on the target web page</li>
                    <li>HTTP response headers and their analysis</li>
                    <li>JavaScript files and their analysis</li>
                    <li>Inline scripts</li>
                    <li>Keywords and comments</li>
                </ul>
         <li><code>--enum-d</code> (<b>Directory Enumeration</b>).</li>
            <p>Performs directory enumeration. Since the tool intentionally uses slow request rates (1-5 seconds per request), it is recommended for highly specific endpoint enumeration, such as APIs.</p>
                <ul>
                    <li>Requires a target with a full URL, including the protocol (e.g., <code>https://example.com</code>).</li>
                    <li>Accepts one target at a time.</li>
                    <li>Can use a default wordlist or a custom file for directories.</li>
                </ul>
        <li><code>--enum-s</code> (<b>Subdomain Enumeration</b>)</li>
            <p>Performs subdomain enumeration. Unlike <code>--enum-d</code>, this mode accepts only a domain as input (e.g., <code>example.com</code>).</p>
            <ul>
                <li>By default, it enumerates subdomains using the HTTPS protocol.</li>
                <li>Accepts one target at a time.</li>
                <li>Can use a default wordlist or a custom file for subdomains.</li>
            </ul>
        <li><code>--http</code></li>
            <p>Works with <code>--enum-s</code> to enable subdomain enumeration over HTTP instead of HTTPS.</p>
        <li><code>-H</code></li>
            <p>Adds custom HTTP headers. If provided, the custom User-Agent header will replace the default.</p>
            <ul><li>Accepts both a string or a file containing headers.</li></ul>
        <li><code>-o</code></li>
            <p>Saves the output to a user-specified file.</p>
            <ul>
                <li>Output will also be printed to the terminal.</li>
                <li>JSON is the recommended format for easier post-processing.</li>
            </ul>
        <li><code>-kw</code></li>
            <p>Adds custom keywords for analysis during crawling.</p>
            <ul><li>Accepts either a string or a file containing keywords.</li></ul>
        <li><code>-wjs</code></li>
            <p>Disables JavaScript file analysis during crawling.</p>
        <li><code>-wha</code></li>
            <p>Disables HTTP header analysis during crawling.</p>
        <li><code>-h</code> (<b>Help</b>)</li>
            <p>Displays the manual, including command examples for easier usage.</p>
    </ol>
</details>

<details><summary><h2><ins>Installation Instructions</ins></h2></summary>
    <p>Follow these steps to set up and use <b>SARA</b>:</p>
    <ol>
        <li><b>Clone the Repository</b></li>
            <pre><code>git clone https://github.com/Kode-n-Rolla/sara.git</code></pre>
        <li><b>Navigate to the Source Directory</b></li>
            <pre><code>cd sara/src</code></pre>
        <li><b>Install Dependencies</b></li>
            <pre><code>pip install -r requirements.txt</code></pre>
            <p>Alternatively, if you encounter an error like <code>× This environment is externally managed</code>, use:</p>
            <pre><code>pip install -r requirements.txt --break-system-packages</code></pre>
        <li><b>Run the Tool</b></li>
            <p>Execute the script with python3 to see available options:</p>
            <pre><code>python3 sara.py -h</code></pre>
        <li><b>Optional: Create a System-wide Command Shortcut</b></li>
            <p>To make it easier to run SARA, you can create a symbolic link (recommended save in /opt first or any your tools directory):</p>
            <pre><code>sudo ln -s "$(pwd)/sara.py" /usr/local/bin/sara</code></pre>
            <p>Now, you can run the tool from anywhere using:</p>
            <pre><code>sara --help</code></pre>
    </ol>
</details>

<details><summary><h2><ins>Versions</ins></h2></summary>
<table>
  <thead>
    <tr>
      <th>Version</th>
      <th>Key Features</th>
      <th>Release Notes</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align='center'><b>1.0</b></td>
      <td width=450>
        <ul>
          <li><code>-t</code>, <code>-c</code>: Crawling and analysis</li>
          <li><code>--enum-d</code>, <code>--enum-s</code> (<code>--http</code>): Enumeration modes</li>
          <li><code>-H</code>, <code>-kw</code>: Custom headers and keywords</li>
          <li><code>-wha</code>, <code>-wjs</code>: Disable header or JS analysis</li>
          <li><code>-o</code>: Save results to a file</li>
          <li><code>--help</code>: Comprehensive manual with examples</li>
        </ul>
      </td>
      <td align='center'>
        Initial release with core functionality including crawling, enumeration, and customizable features for penetration testing and bug bounty tasks.
      </td>
    </tr>
  </tbody>
</table>    
</details>

<h2 align='center'>From Pentester and Bug Hunter to Pentesters and Bug Hunters with love ❤️</h2>

<details><summary><h2>Todo</h2></summary>
    <ol>
        <li>Add images (with folder)</li>
        <li>update Release</li>
        <li>Update default dirs</li>
        <li>Update default subdomains</li>
        <li>Add progress bar to enum modes</li>
        <li>Check installation instructions</li>
        <li>Add some wordlists for api for example</li>
    </ol>
</details>
