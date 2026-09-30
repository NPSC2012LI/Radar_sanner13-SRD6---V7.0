document.addEventListener('DOMContentLoaded', function() {
    const lizhi = document.querySelector('.lizhi'); // 获取lizhi元素
    const circleContainer = document.getElementById('circle-container'); // 获取'circle-container'元素
    const temperatureSelect = document.getElementById('temperatureSelect');
    const animationContainer = document.querySelector('.animation-container'); // 获取形状容器元素
    // const hidden = document.getElementById('hidden');

    let isPaused = false; // 初始状态为非暂停
    let isAnimating = true; // 控制动画变量
    let lastData = null; // 存储最后获取列表数据
    let reData = []; // 存数要更新的最终文本数据
    let dataIndex = 0; // 当前要显示的索引数据
    let prevDisplayedData = null; // 存储上次展示的数据
    let isDataShown = false; // 标记数据是否已经被显示
    let scanCycleCount = 0; // 记录扫描周期数
    const cycleLength = 1; // 扫描周期长度（单位：动画迭代次数）
    let toggleState = '31'; // Pause初始状态值
    let average_temperature = null;  // 初始化平均温度

    // 获取串口列表
    let fixedSerialPorts = [];

    fetch('/get_serial_ports')
        .then(response => response.json())
        .then(data => {
            fixedSerialPorts = data;
            console.log('Serial ports loaded:', fixedSerialPorts);
        })
        .catch(error => {
            console.error('Error loading serial ports:', error);
        });

    // 定义分割的数量
    const divisions = 12;
    const radius =420; //辅助圆的半径即文本距离圆心半径
    const centerX = circleContainer.offsetWidth / 2; // 圆心X坐标
    const centerY = circleContainer.offsetHeight / 2; // 圆心Y坐标

    // 创建分割线
     for (let i = 0; i < divisions; i++) {
        // 创建分割线的DOM元素
        const divisionLine = document.createElement('div');
        // 设置分割线的类名
        divisionLine.className = 'division-line';
        // 计算每条分割线的旋转角度
        const rotationAngle = (i * 360 / divisions) + 90; // 调整以获得正确的位置
        // 设置分割线的旋转样式
        // divisionLine.style.transform = `rotate(${rotationAngle}deg) translate(${radius}px, 0)`; // 从圆的边缘开始旋转
        divisionLine.style.transform = `rotate(${rotationAngle}deg)`; // 从圆心开始旋转
        // 将分割线添加到容器中
        circleContainer.appendChild(divisionLine);
     }

     // 创建标注
    const labels = []; // 用于存储标注元素的数组
    for (let i = 0; i < divisions; i++) {
        // 创建标注的DOM元素
        const label = document.createElement('div');
        label.className = 'label';

        // 设置标注的文本内容
        let angleText = `${Math.floor(i * 360 / divisions)}°`; // 使用 Math.floor 去除小数点
        if (i === 0) {
            angleText = '0°';
        }
        label.textContent = angleText;
        circleContainer.appendChild(label);
        labels.push(label); // 将标注添加到数组中
    }

    // 设置标注位置的函数
    function positionLabels() {
        labels.forEach((label, index) => {
            const angleRadians = index * (2 * Math.PI / divisions);
            const x = centerX + radius * Math.cos(angleRadians) - label.offsetWidth / 2;
            const y = centerY - radius * Math.sin(angleRadians) - label.offsetHeight / 2;

            label.style.position = 'absolute';
            label.style.left = `${x}px`;
            label.style.top = `${y}px`;
        });
    }
    requestAnimationFrame(() => {
        positionLabels();
    });

    // 按钮控制函数
    function toggleAnimation() {
        console.log('Toggle animation called'); // 调试语句
        isPaused = !isPaused; // 切换状态
        isAnimating = !isPaused; // 当暂停时，不进行动画和数据更新
        // 设置 CSS 变量
        lizhi.style.setProperty('--animation-play-state', isPaused ? 'paused' : 'running');

        // 设置 paused 属性来控制动画状态
        lizhi.setAttribute('paused', isPaused ? 'true' : '');

        console.log('Animation paused: ' + isPaused); // 调试语句
        console.log('Current class list:', lizhi.classList); // 调试语句
    }

    // 获取暂停和恢复按钮
    const pauseBtn = document.getElementById('pauseBtn');
    const resumeBtn = document.getElementById('resumeBtn');
    const refreshBtn = document.getElementById('refreshBtn');

    console.log('Pause button:', pauseBtn); // 调试语句
    console.log('Resume button:', resumeBtn); // 调试语句
    console.log('Refresh button:', refreshBtn); // 新增调试语句

    // 设置按钮的初始状态
    // pauseBtn.textContent = 'Pause'; // 假设初始状态是 'Pause'
    pauseBtn.textContent = '暂停'; // 假设初始状态是 'Pause'

    pauseBtn.style.backgroundColor = '#FF0000'; // 假设初始背景颜色是红色
    pauseBtn.classList.add('active'); // 假设初始状态是 'active'
    // 切换按钮状态的函数
    function toggleButtonState(button, text1, text2, color1, color2) {
        const isActive = button.classList.contains('active');
        console.log(`Toggling button state: ${isActive ? 'active' : 'inactive'}`);

        // 根据当前状态设置按钮的文本和背景颜色
        button.textContent = isActive ? text1 : text2;
        button.style.backgroundColor = isActive ? color1 : color2;

        // 强制 CSS 刷新
        if (isActive) {
            // 如果当前是 active 状态，先移除 active 类，触发重绘，然后再次添加
            button.classList.remove('active');
            void button.offsetWidth; // 触发重绘
            button.classList.add('active');
        } else {
            // 如果当前不是 active 状态，先添加 active 类，触发重绘，然后移除
            button.classList.add('active');
            void button.offsetWidth; // 触发重绘
            button.classList.remove('active');
        }

        console.log(isActive ? '暂停' : '开始');
    }
    

    // 发送数据到后端的函数
    function sendDataToBackend(comPort, data) {
        if (!comPort || !data) {
            console.error('Error: Invalid parameters');
            return;
        }

        const url = `/send/${comPort}/${data}`;

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(data);
                // 处理成功的响应
                console.log('Success');
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }

    // 为暂停按钮添加事件监听器
    pauseBtn.addEventListener('click', function() {
        toggleAnimation();

        // 根据当前状态切换发送数据
        const newData = toggleState === '31' ? '30' : '31';
        toggleState = newData;

        // 为fixedSerialPorts列表中的每一个串口发送数据
        fixedSerialPorts.forEach(port => {
            sendDataToBackend(port, newData); // 发送到后端
        });

        // 切换按钮状态
        // toggleButtonState(pauseBtn, toggleState === '30' ? 'Unpause' : 'Pause', toggleState === '31' ? 'Pause' : 'Unpause', toggleState === '30' ? '#0000FF' : '#FF0000', toggleState === '31' ? '#FF0000' : '#0000FF');
        toggleButtonState(pauseBtn, toggleState === '30' ? '开始' : '暂停', toggleState === '31' ? '暂停' : '开始', toggleState === '30' ? '#0000FF' : '#FF0000', toggleState === '31' ? '#FF0000' : '#0000FF');

    });

    // 为恢复按钮添加事件监听器
//    resumeBtn.addEventListener('click', function() {
//        toggleAnimation();
//        toggleButtonState(resumeBtn, 'Pause', 'Unpause', '#FF0000', '#0000FF');
//        sendDataToBackend('COM13', '30'); // 发送0x30到后端
//        console.log('Resume button clicked'); // 调试语句
//    });

    // 新增的刷新按钮事件监听器
    refreshBtn.addEventListener('click', function() {
        fetchData(); // 调用 fetchData 函数刷新数据
        console.log('Refresh button clicked'); // 调试语句
    });

    // 获取motor-control子元素
    const motorControlElements = document.querySelectorAll('.motor-control button');

    // 为每个motor子元素添加事件监听器
    motorControlElements.forEach((button, index) => {
        button.addEventListener('click', function() {
            const dataValues = ['6', '7', '9']; // 要发送的数据值
            const selectedData = dataValues[index]; // 根据索引选择要发送的数据
            const comPort = 'COM14'; // 指定的串口
            const url = `/send_motor/${comPort}/${selectedData}`; // 构建请求URL

            fetch(url) // GET请求
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log(data); // 处理响应数据
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        });
    });

    // 监听temperatureSelect下拉菜单的变化
    temperatureSelect.addEventListener('change', function() {
        // 获取选中的值
        const selectedValue = this.value;
        // 如果有值，则替换默认的 average_temperature
        if (selectedValue !== 'Default') {
            const parsedValue = parseFloat(selectedValue);
            if (!isNaN(parsedValue)) {
                average_temperature = parsedValue;
                console.log("下拉温度值：", average_temperature);
            } else {
                average_temperature = null;  // 重置为默认值
                // console.error("无效的温度值:", selectedValue);
            }
        } else {
            average_temperature = null;  // 重置为默认值
            console.log("下拉温度值已重置为 null");
        }
        fetchData();  // 在下拉菜单值改变时调用 fetchData 函数
    });

    // 绘制水波纹特效
    function drawRipple(x, y, radius) {
        const canvas = document.createElement('canvas');
        canvas.id = 'rippleCanvas'; // 给canvas设置一个ID，方便调试
        canvas.width = 200;
        canvas.height = 200;
        canvas.style.position = 'absolute';
        canvas.style.left = `${x - 100}px`; // 调整位置使其居中
        canvas.style.top = `${y - 100}px`; // 调整位置使其居中
        document.body.appendChild(canvas); // 将canvas添加到body中

        const ctx = canvas.getContext('2d');
        const maxRadius = Math.min(canvas.width, canvas.height) /12; // 设置水波纹最大半径

        function animateRipple() {
            ctx.clearRect(0, 0, canvas.width, canvas.height); // 清除canvas

            // 从中心向外绘制径向渐变
            ctx.beginPath();
            ctx.arc(100, 100, radius, 0, Math.PI * 2, false);
            ctx.closePath();
            const gradient = ctx.createRadialGradient(100, 100, 10, 100, 100, radius);
            gradient.addColorStop(0, 'rgba(0, 0, 255, 0.8)'); // 水波纹开始颜色
            gradient.addColorStop(1, 'rgba(0, 0, 255, 0)');  // 水波纹结束透明色
            ctx.fillStyle = gradient;
            ctx.fill();

            // 逐渐增加半径以模拟水波纹扩散效果
            radius += 0.1;
            if (radius < maxRadius) {
                requestAnimationFrame(animateRipple); // 使用requestAnimationFrame实现平滑动画
            } else {

                // 当半径达到最大值时，移除canvas
                document.body.removeChild(canvas);
            }
        }
        animateRipple();
    }
    // 实时获取新的距离和角度值
    function updateRadarData(newDistance, newAngle) {
        // 获取距离和角度元素的引用
        var distanceElement = document.getElementById('distance');
        var angleElement = document.getElementById('angle');
    }

    // 更新传感器数据表格的函数
    function updateSensorDataTable(data, maxRows = 26) {
        const tableBody = document.getElementById('sensorDataTable').querySelector('tbody');
        tableBody.innerHTML = ''; // 清空现有行
        if (!data || !Array.isArray(data)) {
            console.error('Invalid data format');
            return;
        }
        let rowCount = 0;
        data.forEach(item => {
            if(rowCount >= maxRows) return; // 限制行数添加
            if (item && item.sensor_id !== undefined && item.distance !== undefined && item.angle !== undefined) {
                const row = document.createElement('tr');
                // 添加序号列
                const indexCell = document.createElement('td');
                indexCell.textContent = rowCount + 1; // 自动编号
                row.appendChild(indexCell);
                
                const sensorIdCell = document.createElement('td');
                sensorIdCell.textContent = item.sensor_id; // 使用接口返回的sensor_id作为编号
                row.appendChild(sensorIdCell);

                const distanceCell = document.createElement('td');
                distanceCell.textContent = item.distance !== null ? `${item.distance.toFixed(2)} ` : 'N/A'; // 增加值单位：`${item.distance.toFixed(2)} cm`
                row.appendChild(distanceCell);

                const angleCell = document.createElement('td');
                angleCell.textContent = item.angle !== null ? `${item.angle.toFixed(2)} ` : 'N/A';
                row.appendChild(angleCell);                

                tableBody.appendChild(row);
                rowCount++
            } else {
                console.error('Missing properties in data item:', item);
            }
        });
    }
    // 创建圆点并添加到形状容器
    function createDots() {
        // 清空容器中的旧圆点
        animationContainer.innerHTML = '';

        // 创建81个圆点
        for (let i = 1; i <= 81; i++) {
            const dot = document.createElement('div');
            dot.className = 'dot';
            const row = Math.ceil(i / 9) - 1; // 确定所在的行，从0开始计数
            const col = 8 - ((i - 1) % 9); // 确定所在列的索引，从右往左
            // 根据行列索引计算新的 sensorId
            const sensorId = row * 9 + col + 1;

            dot.setAttribute('id', `dot-${sensorId}`); // 为每个圆点分配一个唯一的ID
            dot.dataset.sensorId = sensorId; // 将编号存储在data属性中
            // dot.dataset.sensorId = i; // 将编号存储在data属性中
            // 设置圆点半径（例如20px）
            dot.style.width = '20px'; // 圆点的宽度
            dot.style.height = '20px'; // 圆点的高度
            dot.style.borderRadius = '50%'; // 确保是圆形
            animationContainer.appendChild(dot);
        }
    }

    

    // 在页面加载时创建圆点
    createDots();   

    // 重置所有圆点颜色的函数
    function resetColor() {
        document.querySelectorAll('.dot').forEach(dot => {
            dot.style.backgroundColor = 'rgba(0, 128, 0, 0.2)'; // 重置为绿色透明度为0.5
        });
    }

    // 更新圆点颜色的函数，并增加绘制外轮廓的逻辑
    function updateDotColors(data, topThree) {
        resetColor(); // 重置所有圆点颜色为绿色
    
        // 确保 data 存在并且不是空数组
        if (!Array.isArray(data) || data.length === 0) {
            console.warn('No data to update dot colors.');
            return;
        }
    
        // 将有符合规则的数据返回的圆点并设置为黄色
        (topThree || []).forEach(item => { // 使用 topThree 或空数组以防未定义
            // 确认 item 包含 sensor_id 属性
            if (item && 'sensor_id' in item) {
                const dot = document.querySelector(`.dot[data-sensor-id="${item.sensor_id}"]`);
                if (dot) {
                    dot.style.backgroundColor = 'yellow'; // 高亮显示黄色
                    // 绘制外轮廓或其他视觉效果
                    // drawOutline(dot);
                } else {
                    console.warn(`No dot found for sensor_id: ${item.sensor_id}`);
                }
            } else {
                console.warn('Item does not contain sensor_id:', item);
            }
        });
    }


    // 筛选并排序数据的函数
    function sortAndSelect(data, count) {
        return data
            .filter(item => item.distance !== undefined && item.angle !== undefined) // 确保distance和angle不为空
            .sort((a, b) => a.distance - b.distance) // 按distance从小到大排序
            .slice(0, count); // 取前count个数据
    }
    
    // 处理跟踪状态消息并定时更新
    function showMessage(message, duration = 1000) {
        const messageDiv = document.getElementById('system-message');
        messageDiv.textContent = message;
        messageDiv.style.display = 'block'; // 显示提示信息
        setTimeout(() => {
            messageDiv.style.opacity = '0'; // 设置透明度为0，模拟隐藏效果
            setTimeout(() => {
                messageDiv.style.display = 'none'; // 真正隐藏提示信息
            }, 500); // 等待透明度变化完成后再隐藏
        }, duration);
    }
    
    
    // 获取数据并更新页面
    function fetchData() {
        if (!isAnimating) {
            // 如果动画暂停，则不获取数据
            return;
        }
        // 使用三元运算符确保 0 也能正确传递
        const temperature = average_temperature !== null ? average_temperature : '';
        fetch(`/data?temperature=${temperature}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // 接口返回的数据格式为数组 [{ distance: 781.27875, angle: 135.0 }, ...]
//                console.log('Fetched data:', data); // 打印获取的数据
                updateSensorDataTable(data); // 更新传感器数据表格
                console.log('Checking new data:', data); // 调试输出
                // 获取距离最小的三个数据项
                const sortedData = data.sort((a, b) => a.distance - b.distance);
                // console.log('sortdeDATA:', sortedData)
                const topThree = sortedData.slice(0, 8);
                // console.log('topThree:', topThree)
                updateDotColors(data, sortedData); // 更新圆点颜色
                // 使用筛选和排序后的数据绘制水波纹动画
                const topTenData = sortAndSelect(data, 9);
                topTenData.forEach(item => {
                    const { distance, angle } = item;
                    const centerX = window.innerWidth / 2;
                    const centerY = window.innerHeight / 2;
                    const radians = (angle + 180) * Math.PI / 180; // 转换角度为弧度
                    const newX = centerX + distance * Math.cos(radians);
                    const newY = centerY + distance * Math.sin(radians);
                    // drawRipple(newX, newY, 5); // 绘制水波纹特效，初始半径为5
                });       
                // 获取页面上的元素
                const distanceElement = document.getElementById('distance');
                const angleElement = document.getElementById('angle');
                const temperatureElement = document.getElementById('temperature');
                // 内部计数器
                let index = 0;
                // 定时更新底部页面
                const updatePage = () => {
                    if (topThree.length > 0) {
                        const item = topThree.shift(); // 取出第一个元素并从数组中移除
                        const { distance, angle } = item;
                        // 更新页面上的元素
                        distanceElement.textContent = distance !== null ? `${distance.toFixed(2)} cm` : 'N/A';
                        angleElement.textContent = angle !== null ? `${angle.toFixed(2)} °` : 'N/A';
                        // 更新页面上温度元素
                        if (average_temperature !== null) {
                            temperatureElement.textContent = `${average_temperature.toFixed(2)} ℃`;
                        } else {
                            temperatureElement.textContent = 'Default ℃';
                        }
                        if (topThree.length === 0) {
                            // 当所有数据项都被展示后，清除定时器
                            clearInterval(intervalId);
                            // 清空页面上的元素
                            distanceElement.textContent = 'N/A';
                            angleElement.textContent = 'N/A';
                        }
                    } else {
                        // 如果没有数据，清空页面上的元素
                        distanceElement.textContent = 'N/A';
                        angleElement.textContent = 'N/A';
                        clearInterval(intervalId);
                    }
                };
                // 设置定时器，每隔?秒更新底部页面
                const intervalId = setInterval(updatePage, 2000);

                lastData = data; // 更新最后获取的数据
            })
            .catch(error => console.error('Error fetching data:', error));
    }

    // 监听扫描线动画
    lizhi.addEventListener('animationiteration', function() {
        scanCycleCount++;
        console.log('Scan cycle count:', scanCycleCount); // 调试输出
        if (scanCycleCount === cycleLength) {
            // 在扫描周期结束时重置标记
            isDataShown = false;
            scanCycleCount = 0; // 重置扫描周期计数器
        }
    });

    // 使用定时器来控制数据处理的频率
    let lastUpdateTimestamp = Date.now();
    const updateInterval = 5000; // 数据更新间隔时间

    setInterval(() => {
        const currentTime = Date.now();
        if (currentTime - lastUpdateTimestamp >= updateInterval && isAnimating && !isPaused) {
            lastUpdateTimestamp = currentTime;
            fetchData(); // 只在动画运行且未暂停时更新数据
        }
    }, 10); // 每10毫秒执行一次，以确保即使在高负载下也能准确更新数据

});